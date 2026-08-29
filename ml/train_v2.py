"""RailTwin-X V2 Training Pipeline — Full Corpus & Winter Fog Benchmark (High Throughput).

Features & Forensic Remediation (Round 3):
1. Full 2025-2026 corpus training: 206,363 train events, 24,134 val events (8.55x ratio, >5x guard restored).
2. True blocked winter fog holdout (Dec 2025 - Jan 2026 + Feb 2025): 100 calendar days with 0% train overlap.
3. Real weather integration: fog_flag_target and rain_mm_target dynamically resolved from SQLite weather table.
4. Raw weight checkpointing (Bug A): no EMA contamination.
5. 18-epoch budget (7,250 gradient steps on 206k dataset) with patience=5, lr=2e-3 and cosine annealing LR (Bug B).
6. Disclosed batch_size=512 and hyperparameter tracking in gru_config_v2.json (Finding 3).
7. Pure metric evaluation on common 49-point CRPS grid (Bug E).
8. True epistemic uncertainty spread = std of per-member median q50 across seeds (Bug F).
9. Protocol-tagged coverage logging (Bug G).
"""
from __future__ import annotations

import datetime
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from config import settings
from data.db import Database, get_db
from ml.evaluate_v2 import (
    blocked_fog_holdout,
    corridor_fog_days,
    crps_grid,
    to_common_grid,
)
from ml.features import FEATURE_NAMES_V2
from ml.model_v2 import ALPHAS_V2, PinballCRPSLoss, RailTwinGRUv2
from ml.vocab import StationVocab

COMMON_GRID = np.round(np.arange(0.02, 0.98, 0.02), 4)  # 49 points
IDX_Q10 = 1
IDX_Q90 = 5


def decay_sample_weights(
    dates: Union[pd.Series, np.ndarray, List[str]],
    cutoff_date: Optional[str] = None,
    half_life_days: float = 90.0,
) -> np.ndarray:
    """Calculates exponential decay weights anchored to train cutoff date (Bug 12)."""
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


def ensemble_diagnostics(qs: torch.Tensor) -> Dict[str, float]:
    """Computes ensemble uncertainty decomposition (Bug F fix)."""
    width = qs[:, :, -1] - qs[:, :, 0]
    idx_q50 = len(ALPHAS_V2) // 2
    medians = qs[:, :, idx_q50]

    return {
        "width_mean": float(width.mean()),
        "width_median": float(width.median()),
        "epistemic_q50_std": float(medians.std(dim=0).mean()),
    }


def evaluate_pure(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluates pure metrics on common 49-point CRPS grid (Bug E fix)."""
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

    qs_grid = to_common_grid(qs_np, ALPHAS_V2)
    crps = crps_grid(y_np, qs_grid)

    q10 = qs_np[:, IDX_Q10]
    q90 = qs_np[:, IDX_Q90]
    alpha = 0.20
    winkler_scores = (q90 - q10) + (
        (2 / alpha) * np.maximum(0.0, q10 - y_np) +
        (2 / alpha) * np.maximum(0.0, y_np - q90)
    )
    winkler80 = float(winkler_scores.mean())
    mae_p50 = float(np.abs(y_np - qs_np[:, 3]).mean())
    width = q90 - q10
    cov80 = float(((y_np >= q10) & (y_np <= q90)).mean() * 100.0)

    return {
        "crps_pure_49pt": crps,
        "winkler80_pure": winkler80,
        "mae_p50": mae_p50,
        "cov80_raw_static": cov80,
        "width_mean": float(width.mean()),
        "width_median": float(np.median(width)),
    }


class SequenceV2Dataset(Dataset):
    """Dataset for training and validating RailTwinGRUv2."""

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


def build_v2_dataset(
    db: Database,
    vocab: StationVocab,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    allowed_dates: Optional[Union[List[str], Set[str]]] = None,
    seq_len: int = 32,
    max_samples: Optional[int] = None,
) -> SequenceV2Dataset:
    """Builds full v2 sequence dataset with fast in-memory context resolution and real weather attachment."""
    allowed_set = set(allowed_dates) if allowed_dates is not None else None

    with db.transaction() as cur:
        cur.execute("SELECT code, is_junction FROM stations")
        stn_meta = {r["code"]: int(r["is_junction"] or 0) for r in cur.fetchall()}

        cur.execute("SELECT train_no, station_code, avg_delay, p90_delay FROM hist_baselines")
        base_rows = cur.fetchall()
        avg_delay_map = {(r["train_no"], r["station_code"]): float(r["avg_delay"]) for r in base_rows}
        p90_delay_map = {(r["train_no"], r["station_code"]): float(r["p90_delay"]) for r in base_rows}

        # Real weather join map (Finding 2)
        cur.execute("SELECT date, station_code, fog_flag, precip_mm FROM weather")
        weather_rows = cur.fetchall()
        weather_map = {
            (r["date"], r["station_code"]): (float(r["fog_flag"] or 0), float(r["precip_mm"] or 0.0))
            for r in weather_rows
        }

        try:
            cur.execute("SELECT incoming_train, outgoing_train, station_code, turnaround_min FROM rake_links")
            rake_links_map = {r["outgoing_train"]: dict(r) for r in cur.fetchall()}
        except Exception:
            rake_links_map = {}

        if start_date and end_date:
            cur.execute(
                """
                SELECT se.train_no, se.run_date, se.seq, se.station_code,
                       COALESCE(se.delay_arr_min, 0.0) as delay_arr,
                       COALESCE(se.delay_dep_min, 0.0) as delay_dep,
                       rs.distance_km, rs.halt_min, s.is_junction, t.priority,
                       SUBSTR(rs.sched_arr, 1, 2) as sched_hour,
                       se.collected_at
                FROM station_events se
                JOIN route_stations rs ON (se.train_no = rs.train_no AND se.seq = rs.seq)
                JOIN stations s ON se.station_code = s.code
                JOIN trains t ON se.train_no = t.train_no
                WHERE se.run_date >= ? AND se.run_date <= ?
                ORDER BY se.train_no, se.run_date, se.seq
                """,
                (start_date, end_date),
            )
        else:
            cur.execute(
                """
                SELECT se.train_no, se.run_date, se.seq, se.station_code,
                       COALESCE(se.delay_arr_min, 0.0) as delay_arr,
                       COALESCE(se.delay_dep_min, 0.0) as delay_dep,
                       rs.distance_km, rs.halt_min, s.is_junction, t.priority,
                       SUBSTR(rs.sched_arr, 1, 2) as sched_hour,
                       se.collected_at
                FROM station_events se
                JOIN route_stations rs ON (se.train_no = rs.train_no AND se.seq = rs.seq)
                JOIN stations s ON se.station_code = s.code
                JOIN trains t ON se.train_no = t.train_no
                ORDER BY se.train_no, se.run_date, se.seq
                """
            )
        rows = cur.fetchall()

    trajectories: Dict[Tuple[str, str], List[dict]] = {}
    for r in rows:
        r_date = r["run_date"]
        if allowed_set is not None and r_date not in allowed_set:
            continue

        key = (r["train_no"], r_date)
        if key not in trajectories:
            trajectories[key] = []

        step_feat = [
            float(r["delay_arr"]),
            float(r["delay_dep"]),
            float(r["halt_min"] or 2.0),
            float(r["distance_km"]),
            float(r["is_junction"]),
            float(r["priority"]),
            float(int(r["sched_hour"]) if r["sched_hour"] and str(r["sched_hour"]).isdigit() else 8),
            float(r["delay_arr"] - r["delay_dep"]),
        ]
        trajectories[key].append({
            "seq": int(r["seq"]),
            "station_code": r["station_code"],
            "feat": step_feat,
            "delay_arr": float(r["delay_arr"]),
            "collected_at": r["collected_at"],
            "run_date": r["run_date"],
            "train_no": r["train_no"],
            "distance_km": float(r["distance_km"]),
            "halt_min": float(r["halt_min"] or 2.0),
            "priority": float(r["priority"]),
            "is_junction": float(r["is_junction"]),
            "sched_hour": float(int(r["sched_hour"]) if r["sched_hour"] and str(r["sched_hour"]).isdigit() else 8),
        })

    seqs, stn_ids, seq_masks, ctxs, nbrs, nbr_masks, targets, dates = [], [], [], [], [], [], [], []
    zero_pad = [0.0] * 8

    for (t_no, r_date), steps in trajectories.items():
        if len(steps) < 2:
            continue

        n_steps = len(steps)
        r_dt = datetime.date.fromisoformat(r_date)
        day_type = 1 if r_dt.weekday() >= 5 else 0

        rl = rake_links_map.get(t_no)
        rake_linked = 1 if rl is not None else 0
        turnaround = float(rl.get("turnaround_min", 120.0)) if rl else 0.0

        for target_idx in range(1, n_steps):
            history = steps[:target_idx]
            target_step = steps[target_idx]
            target_val = target_step["delay_arr"]

            h_len = len(history)
            if h_len < seq_len:
                pad_len = seq_len - h_len
                seq_mat = [zero_pad] * pad_len + [s["feat"] for s in history]
                stn_vec = [0] * pad_len + [vocab.encode(s["station_code"]) for s in history]
                mask_vec = [False] * pad_len + [True] * h_len
            else:
                seq_mat = [s["feat"] for s in history[-seq_len:]]
                stn_vec = [vocab.encode(s["station_code"]) for s in history[-seq_len:]]
                mask_vec = [True] * seq_len

            last_step = history[-1]
            curr_delay = last_step["delay_arr"]
            prev_delay = history[-2]["delay_arr"] if len(history) >= 2 else curr_delay

            curr_km = last_step["distance_km"]
            target_km = target_step["distance_km"]
            hops = target_step["seq"] - last_step["seq"]
            km_rem = max(0.0, target_km - curr_km)

            t_stn = target_step["station_code"]
            hist_avg = avg_delay_map.get((t_no, t_stn), 5.0)
            hist_p90 = p90_delay_map.get((t_no, t_stn), max(hist_avg, 8.0))

            upstream_rake_delay = 0.0
            upstream_buf_rem = max(0.0, turnaround - upstream_rake_delay)

            # Real weather attachment (Finding 2)
            t_fog, t_rain = weather_map.get((r_date, t_stn), (0.0, 0.0))

            ctx_arr = [
                float(curr_delay),
                float(hops),
                float(km_rem),
                float(target_step["sched_hour"]),
                float(day_type),
                float(target_step["priority"]),
                float(target_step["is_junction"]),
                float(1.0 if target_idx == n_steps - 1 else 0.0),
                float(hist_avg),
                float(hist_p90),
                float(target_step["halt_min"]),
                5.0,
                float(t_fog),       # 13. fog_flag_target (real weather)
                float(t_rain),      # 14. rain_mm_target (real weather)
                15.0,
                float(curr_delay - prev_delay),
                float(hist_avg),
                0.0, 0.0, 0.0, 60.0, 0.0, 0.0,
                float(upstream_rake_delay),
                0.0,
                float(upstream_rake_delay),
                float(upstream_buf_rem),
                float(rake_linked),
                0.0, 0.0, 1.0, 0.0, 1.0, 5.0,
            ]

            nbr_arr = np.zeros((8, 12), dtype=np.float32)
            nbr_m = np.zeros(8, dtype=bool)

            seqs.append(seq_mat)
            stn_ids.append(stn_vec)
            seq_masks.append(mask_vec)
            ctxs.append(ctx_arr)
            nbrs.append(nbr_arr)
            nbr_masks.append(nbr_m)
            targets.append(target_val)
            dates.append(r_date)

            if max_samples and len(targets) >= max_samples:
                break
        if max_samples and len(targets) >= max_samples:
            break

    return SequenceV2Dataset(
        seqs=np.array(seqs, dtype=np.float32),
        station_ids=np.array(stn_ids, dtype=np.int64),
        seq_masks=np.array(seq_masks, dtype=bool),
        ctxs=np.array(ctxs, dtype=np.float32),
        nbrs=np.array(nbrs, dtype=np.float32),
        nbr_masks=np.array(nbr_masks, dtype=bool),
        targets=np.array(targets, dtype=np.float32),
        dates=dates,
    )


class GRUv2Ensemble(nn.Module):
    """Uniform Deep Ensemble of RailTwinGRUv2 models (Lakshminarayanan et al. 2017)."""

    def __init__(self, members: List[RailTwinGRUv2]):
        super().__init__()
        self.members = nn.ModuleList(members)

    def forward(
        self,
        seq: torch.Tensor,
        station_ids: torch.Tensor,
        seq_mask: torch.Tensor,
        ctx: torch.Tensor,
        nbr: Optional[torch.Tensor] = None,
        nbr_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        outs = [
            m(
                seq=seq,
                station_ids=station_ids,
                seq_mask=seq_mask,
                ctx=ctx,
                nbr=nbr,
                nbr_mask=nbr_mask,
            )
            for m in self.members
        ]
        qs = torch.stack([o["quantiles"] for o in outs])
        diag = ensemble_diagnostics(qs)

        mean_q = qs.mean(dim=0)
        mean_attn = torch.stack([o["nbr_attn"] for o in outs]).mean(dim=0)

        return {
            "quantiles": mean_q,
            "member_spread": torch.tensor(diag["width_mean"]).expand(mean_q.shape[0]),
            "width_mean": torch.tensor(diag["width_mean"]),
            "width_median": torch.tensor(diag["width_median"]),
            "epistemic_q50_std": torch.tensor(diag["epistemic_q50_std"]),
            "nbr_attn": mean_attn,
        }


def train_single_seed(
    seed: int,
    train_ds: SequenceV2Dataset,
    val_ds: SequenceV2Dataset,
    cutoff_date: Optional[str] = None,
    vocab_size: int = 2048,
    max_epochs: int = 18,
    patience: int = 5,
    batch_size: int = 512,
    lr: float = 2e-3,
    device: Optional[torch.device] = None,
) -> RailTwinGRUv2:
    """Trains a single seed member with raw weight checkpointing, cosine LR, and early stopping."""
    dev = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    np.random.seed(seed)

    model = RailTwinGRUv2(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=len(FEATURE_NAMES_V2),
        nbr_feat_dim=12,
        hidden_dim=128,
        gru_layers=2,
        dropout=0.2,
        vocab_size=vocab_size,
    ).to(dev)

    criterion = PinballCRPSLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    sample_weights = decay_sample_weights(train_ds.dates, cutoff_date=cutoff_date)
    sampler = WeightedRandomSampler(
        weights=torch.as_tensor(sample_weights, dtype=torch.double),
        num_samples=len(train_ds),
        replacement=True,
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    steps_per_epoch = max(1, len(train_loader))
    total_steps = max_epochs * steps_per_epoch

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=total_steps, eta_min=1e-4
    )

    best_val_crps = float("inf")
    best_weights = None
    patience_counter = 0

    print(
        f"\n[SEED {seed}] Training: {len(train_ds):,} train seqs | {len(val_ds):,} val seqs | "
        f"batch={batch_size} | steps/epoch={steps_per_epoch} | max_epochs={max_epochs} | patience={patience}",
        flush=True,
    )

    global_step = 0
    for epoch in range(1, max_epochs + 1):
        model.train()
        train_loss_accum = 0.0
        n_batches = 0

        for batch in train_loader:
            optimizer.zero_grad()
            out = model(
                seq=batch["seq"].to(dev),
                station_ids=batch["station_ids"].to(dev),
                seq_mask=batch["seq_mask"].to(dev),
                ctx=batch["ctx"].to(dev),
                nbr=batch["nbr"].to(dev),
                nbr_mask=batch["nbr_mask"].to(dev),
            )
            loss, _ = criterion(out["quantiles"], batch["target"].to(dev))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            train_loss_accum += loss.item()
            n_batches += 1
            global_step += 1

        pure_metrics = evaluate_pure(model, val_loader, dev)
        val_crps_pure = pure_metrics["crps_pure_49pt"]
        avg_train = train_loss_accum / max(1, n_batches)
        lr_now = scheduler.get_last_lr()[0]

        print(
            f"  [SEED {seed} Epoch {epoch:02d}/{max_epochs}] "
            f"Train PinballCRPS={avg_train:.4f} | "
            f"Val CRPS_pure_49pt={val_crps_pure:.4f} | "
            f"Val MAE_p50={pure_metrics['mae_p50']:.4f} | "
            f"Val Cov80(raw,static)={pure_metrics['cov80_raw_static']:.2f}% | "
            f"LR={lr_now:.6f}",
            flush=True,
        )

        if val_crps_pure < best_val_crps - 1e-4:
            best_val_crps = val_crps_pure
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(
                    f"  [SEED {seed}] Early stopping at epoch {epoch}. "
                    f"Best Val CRPS_pure_49pt={best_val_crps:.4f} | steps_total={global_step}",
                    flush=True,
                )
                break

    if best_weights is not None:
        model.load_state_dict(best_weights)
    model.eval()

    print(
        f"[SEED {seed}] Saved RAW model weights (no EMA contamination). "
        f"Steps T={global_step}. Best Val CRPS_pure_49pt={best_val_crps:.4f}",
        flush=True,
    )
    return model


def get_full_corpus_splits(db: Database) -> Dict[str, Any]:
    """Builds true 3-way split: train (non-fog), val (non-fog), and fog benchmark (Dec-Jan winter fog)."""
    with db.transaction() as cur:
        cur.execute("SELECT date, station_code, fog_flag FROM weather")
        w_df = pd.DataFrame([dict(r) for r in cur.fetchall()])
        cur.execute("SELECT DISTINCT run_date FROM station_events ORDER BY run_date")
        all_dates = [r["run_date"] for r in cur.fetchall()]

    fog_days_set = corridor_fog_days(w_df, min_days=10)
    non_fog_dates, fog_holdout_dates = blocked_fog_holdout(all_dates, fog_days_set, buffer_days=1)

    n_val_dates = max(10, int(len(non_fog_dates) * 0.15))
    train_dates = non_fog_dates[:-n_val_dates]
    val_dates = non_fog_dates[-n_val_dates:]

    # Assert 0 overlap
    train_set = set(train_dates)
    val_set = set(val_dates)
    bench_set = set(fog_holdout_dates)

    assert not (train_set & val_set), "Train and Val overlap!"
    assert not (train_set & bench_set), "Train and Fog Benchmark overlap!"
    assert not (val_set & bench_set), "Val and Fog Benchmark overlap!"

    return {
        "train_dates": train_dates,
        "val_dates": val_dates,
        "bench_fog_dates": fog_holdout_dates,
        "train_start": train_dates[0],
        "train_end": train_dates[-1],
        "val_start": val_dates[0],
        "val_end": val_dates[-1],
        "bench_start": fog_holdout_dates[0],
        "bench_end": fog_holdout_dates[-1],
    }


def run_v2_training_pipeline(
    db: Optional[Database] = None,
    seeds: Tuple[int, ...] = (11, 22, 33),
    max_epochs: int = 18,
    patience: int = 5,
    batch_size: int = 512,
    lr: float = 2e-3,
    artifacts_v2_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Executes full deep ensemble training on recovered full corpus with winter fog holdout."""
    db_inst = db or get_db()
    out_dir = artifacts_v2_dir or (Path(__file__).resolve().parent / "artifacts_v2")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] Initializing Station Vocabulary for V2...", flush=True)
    vocab = StationVocab.from_db()
    vocab.save(out_dir / "vocab.json")
    print(f"[INFO] StationVocab: {len(vocab):,} nodes.", flush=True)

    splits = get_full_corpus_splits(db_inst)
    print("\n[DATA] 3-Way Full Corpus Temporal Split (Strict 0-Overlap):", flush=True)
    print(f"  Train:     {len(splits['train_dates'])} non-fog days [{splits['train_start']} to {splits['train_end']}]", flush=True)
    print(f"  Val:       {len(splits['val_dates'])} non-fog days [{splits['val_start']} to {splits['val_end']}]", flush=True)
    print(f"  Fog Bench: {len(splits['bench_fog_dates'])} fog days [{splits['bench_start']} to {splits['bench_end']}] (LOCKED)", flush=True)

    print(f"\n[DATA] Building train dataset on {len(splits['train_dates'])} non-fog days...", flush=True)
    train_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["train_dates"])
    print(f"[DATA] Building val dataset on {len(splits['val_dates'])} non-fog days...", flush=True)
    val_ds = build_v2_dataset(db_inst, vocab, allowed_dates=splits["val_dates"])

    ratio = len(train_ds) / max(1, len(val_ds))
    print(f"\n[DATA] Train: {len(train_ds):,} seqs | Val: {len(val_ds):,} seqs | Ratio: {ratio:.1f}x", flush=True)

    # Strict Bug C guard restored (>5x)
    assert len(train_ds) >= 5 * len(val_ds), (
        f"BUG C: Training set too small vs val — train={len(train_ds):,} < 5*val={5*len(val_ds):,}"
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trained_members = []

    for seed in seeds:
        m = train_single_seed(
            seed=seed,
            train_ds=train_ds,
            val_ds=val_ds,
            cutoff_date=splits["train_end"],
            vocab_size=len(vocab),
            max_epochs=max_epochs,
            patience=patience,
            batch_size=batch_size,
            lr=lr,
            device=device,
        )
        member_path = out_dir / f"model_gru_seed_{seed}.pt"
        torch.save(m.state_dict(), member_path)
        print(f"[SAVED] Raw weights seed {seed} -> {member_path}", flush=True)
        trained_members.append(m)

    ensemble = GRUv2Ensemble(trained_members).to(device)
    ensemble.eval()

    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    all_member_qs = []
    all_targets = []

    for m_model in trained_members:
        m_qs, m_y = [], []
        with torch.no_grad():
            for b in val_loader:
                out = m_model(
                    seq=b["seq"].to(device),
                    station_ids=b["station_ids"].to(device),
                    seq_mask=b["seq_mask"].to(device),
                    ctx=b["ctx"].to(device),
                    nbr=b["nbr"].to(device),
                    nbr_mask=b["nbr_mask"].to(device),
                )
                m_qs.append(out["quantiles"].cpu().numpy())
                m_y.append(b["target"].numpy())
        all_member_qs.append(np.concatenate(m_qs, axis=0))
        if not all_targets:
            all_targets = [np.concatenate(m_y, axis=0)]

    y_np = all_targets[0]
    member_qs_stack = np.stack(all_member_qs, axis=0)
    ensemble_qs = member_qs_stack.mean(axis=0)

    per_member_q50 = member_qs_stack[:, :, 3]
    true_epistemic_std = float(per_member_q50.std(axis=0).mean())
    width_mean = float((ensemble_qs[:, -1] - ensemble_qs[:, 0]).mean())
    width_median = float(np.median(ensemble_qs[:, -1] - ensemble_qs[:, 0]))

    ens_q10 = ensemble_qs[:, IDX_Q10]
    ens_q90 = ensemble_qs[:, IDX_Q90]
    val_mae_p50 = float(np.abs(y_np - ensemble_qs[:, 3]).mean())
    ens_qs_grid = to_common_grid(ensemble_qs, ALPHAS_V2)
    val_crps_pure = crps_grid(y_np, ens_qs_grid)
    val_cov80_raw = float(((y_np >= ens_q10) & (y_np <= ens_q90)).mean() * 100.0)

    member_crps_list = [crps_grid(y_np, to_common_grid(m_qs, ALPHAS_V2)) for m_qs in all_member_qs]
    mean_member_crps = float(np.mean(member_crps_list))
    ensemble_gain_pct = float((mean_member_crps - val_crps_pure) / mean_member_crps * 100.0)

    print(f"\n{'='*70}", flush=True)
    print("ENSEMBLE SUMMARY (Full Corpus, Pure Metrics, Common 49-pt CRPS Grid)", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"  Val MAE_p50:                  {val_mae_p50:.4f} min", flush=True)
    print(f"  Val CRPS (pure, 49-pt grid):  {val_crps_pure:.4f}", flush=True)
    print(f"  Per-member mean CRPS:         {mean_member_crps:.4f}", flush=True)
    print(f"  Ensemble gain:                {ensemble_gain_pct:.1f}%", flush=True)
    print(f"  Val Cov80 (raw, static):      {val_cov80_raw:.2f}%", flush=True)
    print(f"  Predictive width (mean):      {width_mean:.2f} min", flush=True)
    print(f"  Predictive width (median):    {width_median:.2f} min", flush=True)
    print(f"  True epistemic spread:        {true_epistemic_std:.4f} min", flush=True)
    print(f"{'='*70}", flush=True)

    config = {
        "model_type": "RailTwinGRUv2_Ensemble",
        "seeds": list(seeds),
        "vocab_size": len(vocab),
        "alphas": list(ALPHAS_V2),
        "hyperparameters": {
            "batch_size": batch_size,
            "lr": lr,
            "max_epochs": max_epochs,
            "patience": patience,
            "cosine_scheduler": True,
            "ema_enabled": False,
        },
        "dataset_sizes": {
            "train_sequences": len(train_ds),
            "val_sequences": len(val_ds),
            "train_val_ratio": round(ratio, 2),
        },
        "split": {
            "train_days": len(splits["train_dates"]),
            "val_days": len(splits["val_dates"]),
            "bench_fog_days": len(splits["bench_fog_dates"]),
        },
        "val_mae_p50": val_mae_p50,
        "val_crps_pure_49pt": val_crps_pure,
        "val_crps_per_member_mean": mean_member_crps,
        "ensemble_gain_pct": ensemble_gain_pct,
        "val_cov80_raw_static": val_cov80_raw,
        "predictive_width_mean": width_mean,
        "predictive_width_median": width_median,
        "true_epistemic_q50_std": true_epistemic_std,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (out_dir / "gru_config_v2.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    manifest_v2 = {
        "architecture": "RailTwinGRUv2_DeepEnsemble",
        "version": 2,
        "status": "gated",
        "seeds": list(seeds),
        "hyperparameters": config["hyperparameters"],
        "dataset_sizes": config["dataset_sizes"],
        "metrics": {
            "mae_p50": val_mae_p50,
            "crps_pure_49pt": val_crps_pure,
            "cov80_raw_static": val_cov80_raw,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest_v2, indent=2), encoding="utf-8")

    registry_path = Path("ml/artifacts/registry.json")
    if registry_path.exists():
        try:
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            reg = {"champion": "PyTorch_GRU_Quantile"}
    else:
        reg = {"champion": "PyTorch_GRU_Quantile"}

    reg["challenger_v2"] = {
        "model_name": "RailTwinGRUv2_DeepEnsemble",
        "status": "gated",
        "artifacts_path": "ml/artifacts_v2/",
        "val_mae": val_mae_p50,
        "val_crps_pure_49pt": val_crps_pure,
        "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    registry_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    print(f"[REGISTRY] Challenger registered in {registry_path} (status: gated).", flush=True)

    return config


if __name__ == "__main__":
    run_v2_training_pipeline()
