"""RailTwin-X v3 Official Gate Shootout (Phase F).

Unseals BENCH_v3 (fog core) and BENCH_NORMAL, evaluates the trained v3 Deep Ensemble
against the v1 Champion across:
1. OVERALL BENCH_v3 (Fog Core holdout: 2025-11-30 to 2026-01-01)
2. BENCH_NORMAL (Normal holdout: 2026-02-01 to 2026-08-31)
3. CLASS: Mail (specialist row, >=60,000 events)
4. CLASS: Passenger (specialist row, >=60,000 events)

Computes paired sample-level Wilcoxon signed-rank test and Diebold-Mariano HAC test.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.stats as stats
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from data.db import Database, get_db
from ml.evaluate_v2 import crps_grid, to_common_grid
from ml.features_v3 import ALPHAS, FEATURE_NAMES_V3, V3FeatureBuilder
from ml.model_seq import NonCrossingGRUQuantileModel
from ml.model_v3 import ALPHAS_V3, GRUv3Ensemble, RailTwinGRUv3
from ml.train_v3 import build_dataset_from_snapshots
from ml.vocab import StationVocab

COMMON_GRID = np.round(np.linspace(0.02, 0.98, 49), 4)


def diebold_mariano_hac(e_champ: np.ndarray, e_v3: np.ndarray, max_lag: int = 14) -> Tuple[float, float]:
    """Diebold-Mariano test with Newey-West HAC variance estimator for serial correlation."""
    d = e_champ - e_v3  # positive d means v3 has lower error
    T = len(d)
    d_mean = np.mean(d)

    # Sample autocovariances
    gamma_0 = np.var(d)
    gamma_sum = 0.0
    for l in range(1, max_lag + 1):
        weight = 1.0 - (l / (max_lag + 1.0))  # Bartlett kernel
        gamma_l = np.mean((d[l:] - d_mean) * (d[:-l] - d_mean))
        gamma_sum += 2.0 * weight * gamma_l

    lr_var = (gamma_0 + gamma_sum) / T
    if lr_var <= 1e-12:
        return 0.0, 1.0

    dm_stat = float(d_mean / np.sqrt(lr_var))
    # Two-sided p-value from standard normal
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(dm_stat))))
    return dm_stat, p_val


def load_v1_champion(device: torch.device) -> nn.Module:
    """Loads the v1 Champion model with strict native forward call."""
    ckpt_path = Path("ml/artifacts/model_gru_champion.pt")
    if not ckpt_path.exists():
        ckpt_path = Path("ml/artifacts/model_gru_best.pt")

    # Native v1 GRU architecture
    champ = NonCrossingGRUQuantileModel(
        feat_dim=8,
        hidden_dim=128,
        gru_layers=2,
        dropout=0.0,
        vocab_size=2048,
    ).to(device)

    state = torch.load(ckpt_path, map_location=device, weights_only=False)
    if "model_state" in state:
        champ.load_state_dict(state["model_state"], strict=False)
    else:
        champ.load_state_dict(state, strict=False)
    champ.eval()
    return champ


def load_v3_ensemble(vocab_size: int, device: torch.device) -> GRUv3Ensemble:
    """Loads the 3-seed v3 Deep Ensemble."""
    members = []
    for seed in (11, 22, 33):
        m = RailTwinGRUv3(
            seq_feat_dim=8,
            station_emb_dim=8,
            ctx_dim=24,
            nbr_feat_dim=12,
            hidden_dim=128,
            gru_layers=2,
            vocab_size=vocab_size,
            n_experts=3,
            gate_dim=6,
        ).to(device)
        ckpt_path = Path(f"ml/artifacts_v3/model_gru_v3_seed_{seed}.pt")
        m.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))
        m.eval()
        members.append(m)

    return GRUv3Ensemble(members).to(device)


def evaluate_shootout_split(
    champ_model: nn.Module,
    v3_ensemble: nn.Module,
    db: Database,
    vocab: StationVocab,
    where_clause: str,
    device: torch.device,
) -> Dict[str, Any]:
    """Runs a paired sample-level shootout between Champion and v3 on a specific split."""
    ds = build_dataset_from_snapshots(db, vocab, where_clause)
    if len(ds) == 0:
        return {"n": 0, "win": False}

    loader = DataLoader(ds, batch_size=512, shuffle=False)

    champ_errs, v3_errs = [], []
    champ_qs_all, v3_qs_all, targets_all = [], [], []

    with torch.no_grad():
        for b in loader:
            seq = b["seq"].to(device)
            stn_ids = b["station_ids"].to(device)
            seq_m = b["seq_mask"].to(device)
            ctx = b["ctx"].to(device)
            nbr = b["nbr"].to(device)
            nbr_m = b["nbr_mask"].to(device)
            y = b["target"].numpy()

            # 1. Champion: native 8-dim forward call (Phase A1 fix)
            q10_c, q50_c, q90_c = champ_model(seq)
            champ_q50 = q50_c.cpu().numpy().flatten()

            # 2. v3 Ensemble
            out_v3 = v3_ensemble(
                seq=seq,
                station_ids=stn_ids,
                seq_mask=seq_m,
                ctx=ctx,
                nbr=nbr,
                nbr_mask=nbr_m,
            )
            v3_q50 = out_v3["quantiles"][:, 3].cpu().numpy().flatten()
            v3_qs_all.append(out_v3["quantiles"].cpu().numpy())

            champ_errs.append(np.abs(y - champ_q50))
            v3_errs.append(np.abs(y - v3_q50))
            targets_all.append(y)

    e_champ = np.concatenate(champ_errs)
    e_v3 = np.concatenate(v3_errs)
    y_all = np.concatenate(targets_all)
    v3_qs_np = np.concatenate(v3_qs_all)

    # Common grid CRPS for v3
    v3_grid = to_common_grid(v3_qs_np, ALPHAS_V3)
    v3_crps = crps_grid(y_all, v3_grid)

    champ_mae = float(np.mean(e_champ))
    v3_mae = float(np.mean(e_v3))
    delta_mae = v3_mae - champ_mae

    # Coverage 80%
    q10_v3 = v3_qs_np[:, 1]
    q90_v3 = v3_qs_np[:, 5]
    cov80 = float(np.mean((y_all >= q10_v3) & (y_all <= q90_v3)) * 100.0)

    # Paired Wilcoxon Signed-Rank Test
    diff = e_champ - e_v3
    non_zero = diff[diff != 0.0]
    if len(non_zero) > 20:
        w_stat, p_val = stats.wilcoxon(diff, alternative="greater")
    else:
        p_val = 1.0

    # Diebold-Mariano HAC test
    dm_stat, dm_pval = diebold_mariano_hac(e_champ, e_v3)

    is_win = (delta_mae < 0.0) and (p_val < 0.01)

    return {
        "n_samples": len(e_champ),
        "champ_mae": round(champ_mae, 3),
        "v3_mae": round(v3_mae, 3),
        "delta_mae": round(delta_mae, 3),
        "v3_crps": round(v3_crps, 3),
        "cov80_pct": round(cov80, 2),
        "wilcoxon_pval": p_val,
        "dm_stat": round(dm_stat, 3),
        "dm_pval": dm_pval,
        "win": is_win,
    }


def run_honest_champion_gate(db: Optional[Database] = None) -> Dict[str, Any]:
    """Executes the official unsealed Phase F Shootout."""
    db_inst = db or get_db()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    vocab = StationVocab.load("ml/artifacts_v3/vocab.json")
    champ_model = load_v1_champion(dev)
    v3_ensemble = load_v3_ensemble(len(vocab), dev)

    splits_to_evaluate = [
        ("Row 1: OVERALL BENCH_v3 (Fog Core)", "run_date BETWEEN '2025-11-30' AND '2026-01-01'"),
        ("Row 2: BENCH_NORMAL (2026 Normal Days)", "run_date >= '2026-02-01'"),
        ("Row 3: CLASS: Mail (>=60k events)", "train_no IN (SELECT train_no FROM trains WHERE class = 'mail') AND run_date >= '2025-11-30'"),
        ("Row 4: CLASS: Passenger (>=60k events)", "train_no IN (SELECT train_no FROM trains WHERE class = 'passenger') AND run_date >= '2025-11-30'"),
    ]

    print("\n" + "=" * 88)
    print("RAILTWIN-X v3 OFFICIAL GATE SHOOTOUT — UNSEALED BENCHMARKS")
    print("=" * 88)
    print(f"{'Evaluation Row':<38} {'N':<7} {'Champ MAE':<10} {'v3 MAE':<8} {'Delta':<8} {'p-val':<8} {'DM Stat':<8} {'Win?'}")
    print("-" * 88)

    results = {}
    all_win = True

    for label, clause in splits_to_evaluate:
        res = evaluate_shootout_split(champ_model, v3_ensemble, db_inst, vocab, clause, dev)
        results[label] = res
        win_str = "YES" if res["win"] else "NO"
        if not res["win"]:
            all_win = False
        print(
            f"{label:<38} {res['n_samples']:<7} {res['champ_mae']:<10.2f} {res['v3_mae']:<8.2f} "
            f"{res['delta_mae']:<8.2f} {res['wilcoxon_pval']:<8.4f} {res['dm_stat']:<8.2f} {win_str}"
        )

    print("=" * 88)

    # Decision logic
    fog_res = results["Row 1: OVERALL BENCH_v3 (Fog Core)"]
    norm_res = results["Row 2: BENCH_NORMAL (2026 Normal Days)"]

    if all_win:
        decision = "ACCEPT_FULL_CHAMPION"
        print("[GATE DECISION] FULL ACCEPTANCE — v3 wins on ALL benchmarks and specialist classes.")
    elif fog_res["win"] and (norm_res["delta_mae"] <= 0.05 * norm_res["champ_mae"]):
        decision = "ACCEPT_FOG_SPECIALIST"
        print("[GATE DECISION] CONDITIONAL ACCEPTANCE — v3 accepted as Fog Specialist.")
    else:
        decision = "REJECT_CHAMPION_STAYS"
        print("[GATE DECISION] REJECT — Champion remains active in production.")

    out_manifest = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": decision,
        "results": results,
        "human_ack_required": True,
    }

    with open("ml/artifacts_v3/shootout_manifest.json", "w", encoding="utf-8") as f:
        json.dump(out_manifest, f, indent=2)

    return out_manifest


if __name__ == "__main__":
    run_honest_champion_gate()
