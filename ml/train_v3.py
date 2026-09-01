"""RailTwin-X v3 Training Pipeline — The One Retrain (Phase E).

Executes the official v3 retrain under strict scientific invariants:
1. TRAIN_v3 (2025-02-08 to 2025-10-31) and VAL_v3 (2025-11-01 to 2025-11-29) ONLY.
2. BENCH_v3 (fog holdout) and BENCH_NORMAL remain SEALED until Phase F.
3. 3 seeds: {11, 22, 33}.
4. Max 40 epochs, patience 8, CosineAnnealingLR (2e-3 -> 1e-4), batch_size=512.
5. NO EMA: raw weight checkpointing only.
6. Exponential decay sampling (half-life = 90 days).
7. Gated RegimeMoEHead with auxiliary load-balancing loss.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from data.db import Database, get_db
from ml.evaluate_v2 import crps_grid, to_common_grid
from ml.features_v3 import ALPHAS, FEATURE_NAMES_V3, V3FeatureBuilder
from ml.model_v3 import ALPHAS_V3, PinballCRPSLoss, RailTwinGRUv3
from ml.vocab import StationVocab

COMMON_GRID = np.round(np.linspace(0.02, 0.98, 49), 4)
IDX_Q10 = 1
IDX_Q50 = 3
IDX_Q90 = 5


def decay_sample_weights(
    dates: List[str],
    cutoff_date: Optional[str] = None,
    half_life_days: float = 90.0,
) -> np.ndarray:
    """Calculates exponential decay weights anchored to train cutoff date."""
    dt_series = pd.Series(pd.to_datetime(dates))
    if cutoff_date is not None:
        anchor_dt = pd.to_datetime(cutoff_date)
    else:
        anchor_dt = dt_series.max()
    age_days = (anchor_dt - dt_series).dt.total_seconds().to_numpy(dtype=float) / 86400.0
    age_days = np.maximum(0.0, age_days)
    lam = math.log(2.0) / half_life_days
    weights = np.exp(-lam * age_days)
    return weights / weights.sum()


class SnapshotV3Dataset(Dataset):
    """PyTorch dataset reading from materialized feature_snapshots_v3."""

    def __init__(
        self,
        seqs: np.ndarray,
        station_ids: np.ndarray,
        seq_masks: np.ndarray,
        ctxs: np.ndarray,
        nbrs: np.ndarray,
        nbr_masks: np.ndarray,
        targets: np.ndarray,
        dates: List[str],
    ):
        self.seqs = torch.tensor(seqs, dtype=torch.float32)
        self.station_ids = torch.tensor(station_ids, dtype=torch.long)
        self.seq_masks = torch.tensor(seq_masks, dtype=torch.bool)
        self.ctxs = torch.tensor(ctxs, dtype=torch.float32)
        self.nbrs = torch.tensor(nbrs, dtype=torch.float32)
        self.nbr_masks = torch.tensor(nbr_masks, dtype=torch.bool)
        self.targets = torch.tensor(targets, dtype=torch.float32)
        self.dates = dates

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "seq": self.seqs[idx],
            "station_ids": self.station_ids[idx],
            "seq_mask": self.seq_masks[idx],
            "ctx": self.ctxs[idx],
            "nbr": self.nbrs[idx],
            "nbr_mask": self.nbr_masks[idx],
            "target": self.targets[idx],
        }


def build_dataset_from_snapshots(
    db: Database,
    vocab: StationVocab,
    date_clause: str,
    seq_len: int = 8,
    max_samples: Optional[int] = None,
) -> SnapshotV3Dataset:
    """Builds PyTorch dataset from feature_snapshots_v3 and historical sequence trajectories."""
    con = db.get_connection()
    query = f"""
    SELECT train_no, run_date, target_station, as_of, horizon_min, y,
           f_current_delay, f_delay_velocity, f_staleness_vel, f_km_remaining,
           f_sched_min_to_target, f_sin_hour, f_cos_hour, f_day_of_week,
           f_target_is_terminus, f_hist_recency_avg, f_hist_p90, f_train_priority,
           f_exp_decay_ahead, f_opposing_ahead, f_max_delay_ahead,
           f_route_ahead_occ, f_rake_net_delay, f_rake_buffer_pct, f_rake_linked,
           f_tsr_count, f_tsr_max_slow, f_fog_dawn, f_rain_mm, f_festival_prox
    FROM feature_snapshots_v3
    WHERE {date_clause}
    ORDER BY run_date ASC, train_no ASC
    """
    if max_samples:
        query += f" LIMIT {max_samples}"

    rows = con.execute(query).fetchall()

    # Pre-cache sequence events per train_no + run_date
    cur_events = con.execute(
        """
        SELECT train_no, run_date, seq, station_code,
               COALESCE(delay_arr_min, 0.0) as delay_arr,
               COALESCE(delay_dep_min, 0.0) as delay_dep,
               COALESCE(event_time, collected_at) as event_time
        FROM station_events
        ORDER BY train_no, run_date, seq
        """
    )
    all_events = cur_events.fetchall()
    events_by_journey: Dict[Tuple[str, str], List[sqlite3.Row]] = {}
    for r in all_events:
        events_by_journey.setdefault((str(r["train_no"]), str(r["run_date"])), []).append(r)

    seqs, stn_ids, seq_masks, ctxs, nbrs, nbr_masks, targets, dates = [], [], [], [], [], [], [], []
    zero_pad = [0.0] * 8

    for r in rows:
        t_no = str(r["train_no"])
        r_date = str(r["run_date"])
        as_of_str = str(r["as_of"])
        y = float(r["y"])

        # Extract 24-dim context vector
        ctx_vec = [float(r[col_idx]) for col_idx in range(6, 30)]

        # Extract past observed events on this journey <= as_of
        j_events = events_by_journey.get((t_no, r_date), [])
        obs = [e for e in j_events if str(e["event_time"]) <= as_of_str]

        feat_steps = []
        stn_vec = []
        for e in obs:
            d_arr = float(e["delay_arr"])
            d_dep = float(e["delay_dep"])
            stn_code = str(e["station_code"])
            feat_steps.append([d_arr, d_dep, 2.0, 0.0, 0.0, 3.0, 8.0, d_arr - d_dep])
            stn_vec.append(vocab.encode(stn_code))

        h_len = len(feat_steps)
        if h_len < seq_len:
            pad_len = seq_len - h_len
            seq_mat = [zero_pad] * pad_len + feat_steps
            stn_final = [0] * pad_len + stn_vec
            mask_vec = [False] * pad_len + [True] * h_len
        else:
            seq_mat = feat_steps[-seq_len:]
            stn_final = stn_vec[-seq_len:]
            mask_vec = [True] * seq_len

        nbr_arr = np.zeros((8, 12), dtype=np.float32)
        nbr_m = np.zeros(8, dtype=bool)

        seqs.append(seq_mat)
        stn_ids.append(stn_final)
        seq_masks.append(mask_vec)
        ctxs.append(ctx_vec)
        nbrs.append(nbr_arr)
        nbr_masks.append(nbr_m)
        targets.append(y)
        dates.append(r_date)

    con.close()

    return SnapshotV3Dataset(
        seqs=np.array(seqs, dtype=np.float32),
        station_ids=np.array(stn_ids, dtype=np.int64),
        seq_masks=np.array(seq_masks, dtype=bool),
        ctxs=np.array(ctxs, dtype=np.float32),
        nbrs=np.array(nbrs, dtype=np.float32),
        nbr_masks=np.array(nbr_masks, dtype=bool),
        targets=np.array(targets, dtype=np.float32),
        dates=dates,
    )


def evaluate_v3_pure(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluates model performance on the common 49-point continuous grid."""
    all_qs, all_y = [], []
    model.eval()
    with torch.no_grad():
        for b in loader:
            out = model(
                seq=b["seq"].to(device),
                station_ids=b["station_ids"].to(device),
                seq_mask=b["seq_mask"].to(device),
                ctx=b["ctx"].to(device),
                nbr=b["nbr"].to(device),
                nbr_mask=b["nbr_mask"].to(device),
            )
            all_qs.append(out["quantiles"].cpu().numpy())
            all_y.append(b["target"].numpy())

    qs_np = np.concatenate(all_qs, axis=0)
    y_np = np.concatenate(all_y, axis=0)

    qs_grid = to_common_grid(qs_np, ALPHAS_V3)
    crps = crps_grid(y_np, qs_grid)

    q10 = qs_np[:, IDX_Q10]
    q90 = qs_np[:, IDX_Q90]
    mae_p50 = float(np.abs(y_np - qs_np[:, IDX_Q50]).mean())
    cov80 = float(((y_np >= q10) & (y_np <= q90)).mean() * 100.0)

    return {
        "crps_pure_49pt": crps,
        "mae_p50": mae_p50,
        "cov80_raw_static": cov80,
    }


def train_single_seed_v3(
    seed: int,
    train_ds: SnapshotV3Dataset,
    val_ds: SnapshotV3Dataset,
    vocab_size: int = 2048,
    max_epochs: int = 40,
    patience: int = 8,
    batch_size: int = 512,
    lr: float = 2e-3,
    min_lr: float = 1e-4,
    device: Optional[torch.device] = None,
) -> RailTwinGRUv3:
    """Trains one seed of RailTwinGRUv3 with CosineAnnealingLR and raw weight checkpointing."""
    dev = device or torch.device("cpu")
    torch.manual_seed(seed)
    np.random.seed(seed)

    print(f"\n[SEED {seed}] Launching Training (N_train={len(train_ds):,}, N_val={len(val_ds):,})...", flush=True)

    weights = decay_sample_weights(train_ds.dates, cutoff_date="2025-10-31", half_life_days=90.0)
    sampler = WeightedRandomSampler(weights=weights, num_samples=len(train_ds), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = RailTwinGRUv3(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=24,
        nbr_feat_dim=12,
        hidden_dim=128,
        gru_layers=2,
        dropout=0.0,
        vocab_size=vocab_size,
        n_experts=3,
        gate_dim=6,
    ).to(dev)

    criterion = PinballCRPSLoss(alphas=ALPHAS_V3, aux_weight=0.01).to(dev)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=min_lr)

    best_val_crps = float("inf")
    best_weights = None
    patience_counter = 0
    global_step = 0

    for epoch in range(1, max_epochs + 1):
        model.train()
        train_loss_accum = 0.0
        n_batches = 0

        for b in train_loader:
            optimizer.zero_grad()
            out = model(
                seq=b["seq"].to(dev),
                station_ids=b["station_ids"].to(dev),
                seq_mask=b["seq_mask"].to(dev),
                ctx=b["ctx"].to(dev),
                nbr=b["nbr"].to(dev),
                nbr_mask=b["nbr_mask"].to(dev),
            )
            loss, loss_dict = criterion(out["quantiles"], b["target"].to(dev), out["aux_loss"])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss_accum += loss.item()
            n_batches += 1
            global_step += 1

        scheduler.step()
        pure_metrics = evaluate_v3_pure(model, val_loader, dev)
        val_crps = pure_metrics["crps_pure_49pt"]
        avg_train = train_loss_accum / max(1, n_batches)
        cur_lr = scheduler.get_last_lr()[0]

        print(
            f"  [SEED {seed} Epoch {epoch:02d}/{max_epochs}] "
            f"Train Loss={avg_train:.4f} | "
            f"Val CRPS={val_crps:.4f} | "
            f"Val MAE={pure_metrics['mae_p50']:.4f} | "
            f"Val Cov80={pure_metrics['cov80_raw_static']:.2f}% | "
            f"LR={cur_lr:.6f}",
            flush=True,
        )

        if val_crps < best_val_crps - 1e-4:
            best_val_crps = val_crps
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  [SEED {seed}] Early stopping at epoch {epoch}. Best Val CRPS={best_val_crps:.4f}", flush=True)
                break

    if best_weights is not None:
        model.load_state_dict(best_weights)
    model.eval()

    print(f"[SEED {seed}] Checkpoint saved (RAW weights, no EMA). Best Val CRPS={best_val_crps:.4f}", flush=True)
    return model


def run_v3_training_pipeline(
    db: Optional[Database] = None,
    seeds: Tuple[int, ...] = (11, 22, 33),
    max_epochs: int = 40,
    patience: int = 8,
    batch_size: int = 512,
    lr: float = 2e-3,
    min_lr: float = 1e-4,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Executes the full RailTwin-X v3 retraining pipeline."""
    db_inst = db or get_db()
    artifacts_dir = out_dir or Path("ml/artifacts_v3")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("RAILTWIN-X v3 RETRAINING PIPELINE (THE ONE RETRAIN)")
    print("=" * 75)

    vocab = StationVocab.from_db(str(db_inst.db_path))
    vocab.save(artifacts_dir / "vocab.json")

    print("[INFO] Building TRAIN_v3 dataset (2025-02-08 to 2025-10-31)...", flush=True)
    train_ds = build_dataset_from_snapshots(
        db_inst, vocab, date_clause="run_date BETWEEN '2025-02-08' AND '2025-10-31'"
    )
    print("[INFO] Building VAL_v3 dataset (2025-11-01 to 2025-11-29)...", flush=True)
    val_ds = build_dataset_from_snapshots(
        db_inst, vocab, date_clause="run_date BETWEEN '2025-11-01' AND '2025-11-29'"
    )

    trained_members = []
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    for s in seeds:
        m = train_single_seed_v3(
            seed=s,
            train_ds=train_ds,
            val_ds=val_ds,
            vocab_size=len(vocab),
            max_epochs=max_epochs,
            patience=patience,
            batch_size=batch_size,
            lr=lr,
            min_lr=min_lr,
            device=dev,
        )
        ckpt_path = artifacts_dir / f"model_gru_v3_seed_{s}.pt"
        torch.save(m.state_dict(), ckpt_path)
        trained_members.append(m)

    # Save gru_config_v3.json
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    ens = RailTwinGRUv3(vocab_size=len(vocab), hidden_dim=128)
    ens_metrics = evaluate_v3_pure(trained_members[0], val_loader, dev)

    config_v3 = {
        "model_type": "RailTwinGRUv3_RegimeMoE",
        "feature_version": 3,
        "feature_count": 24,
        "features": FEATURE_NAMES_V3,
        "seeds": list(seeds),
        "vocab_size": len(vocab),
        "hidden_dim": 128,
        "gru_layers": 2,
        "n_experts": 3,
        "gate_dim": 6,
        "quantiles": list(ALPHAS_V3),
        "hyperparameters": {
            "batch_size": batch_size,
            "max_epochs": max_epochs,
            "patience": patience,
            "lr_start": lr,
            "lr_end": min_lr,
            "scheduler": "CosineAnnealingLR",
            "weight_decay": 1e-4,
            "decay_sampler_halflife_days": 90.0,
            "ema": False,
        },
        "val_metrics": ens_metrics,
        "splits": {
            "train": "2025-02-08 to 2025-10-31",
            "val": "2025-11-01 to 2025-11-29",
            "bench_fog": "2025-11-30 to 2026-01-01 (SEALED)",
            "bench_normal": "2026-02-01 to 2026-08-31 (SEALED)",
        },
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    config_path = artifacts_dir / "gru_config_v3.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_v3, f, indent=2)

    print(f"\n[SUCCESS] Retrain complete. Artifacts saved to {artifacts_dir}/")
    return config_v3


if __name__ == "__main__":
    run_v3_training_pipeline()
