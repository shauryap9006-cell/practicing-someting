"""Candidate Shootout — TASK-2 of 19_RECOVERY Sprint.

Trains 3 candidates (C1=30d, C2=full+7d half-life, C3=full+14d half-life) and
evaluates all 4 (C0=restored, C1, C2, C3) on IDENTICAL test window
2026-08-23 -> 2026-08-29 using purged protocol.

Winner = argmin overall MAE (tie-break: 1h MAE).
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats

from config import settings
from data.db import Database, get_db
from ml.features import FEATURE_NAMES
from ml.snapshots import SnapshotGenerator

ARTIFACTS_DIR = settings.ARTIFACTS_DIR
TEST_START = "2026-08-23"
TEST_END = "2026-08-29"
TRAIN_CUTOFF = "2026-08-22"


def compute_winkler(y, p10, p90, alpha=0.20):
    width = p90 - p10
    under = (2.0 / alpha) * np.maximum(0.0, p10 - y)
    over  = (2.0 / alpha) * np.maximum(0.0, y - p90)
    return float(np.mean(width + under + over))


def evaluate_models_on_test(test_df: pd.DataFrame, models_dir: Path, label: str) -> dict:
    """Load 6 LightGBM models from models_dir and evaluate on test_df."""
    models = {}
    for q in [10, 50, 90]:
        for mtype in ["direct", "delta"]:
            p = models_dir / f"model_{mtype}_q{q}.txt"
            if p.exists():
                models[f"{mtype}_q{q}"] = lgb.Booster(model_file=str(p))
            else:
                print(f"  [WARN] {label}: missing model {p}")

    if "direct_q50" not in models:
        return {"error": "direct_q50 missing"}

    # B1: frozen delay
    y_true = test_df["target_direct_delay"].values
    b1 = test_df["current_delay"].values
    b1_mae = float(np.mean(np.abs(b1 - y_true)))

    # Model predictions per horizon
    def horizon_metrics(mask, name):
        if not mask.any():
            return None
        y_h = y_true[mask]
        feat_h = test_df[mask][FEATURE_NAMES]
        p50 = models["direct_q50"].predict(feat_h) if "direct_q50" in models else b1[mask]
        p10 = models["direct_q10"].predict(feat_h) if "direct_q10" in models else p50 - 5
        p90 = models["direct_q90"].predict(feat_h) if "direct_q90" in models else p50 + 10
        b1_h = b1[mask]
        mae = float(np.mean(np.abs(p50 - y_h)))
        cov = float(np.mean((y_h >= p10) & (y_h <= p90))) * 100.0
        wink = compute_winkler(y_h, p10, p90)
        mae_b1 = float(np.mean(np.abs(b1_h - y_h)))
        return {"n": int(mask.sum()), "mae": mae, "cov": cov, "winkler": wink,
                "mae_b1": mae_b1}

    km = test_df["km_remaining"].values
    h1 = horizon_metrics(km <= 90, "1h")
    h3 = horizon_metrics((km > 90) & (km <= 250), "3h")
    h6 = horizon_metrics(km > 250, "6h")

    # Overall
    p50_all = models["direct_q50"].predict(test_df[FEATURE_NAMES])
    overall_mae = float(np.mean(np.abs(p50_all - y_true)))
    p10_all = models["direct_q10"].predict(test_df[FEATURE_NAMES]) if "direct_q10" in models else p50_all - 5
    p90_all = models["direct_q90"].predict(test_df[FEATURE_NAMES]) if "direct_q90" in models else p50_all + 10
    overall_cov = float(np.mean((y_true >= p10_all) & (y_true <= p90_all))) * 100.0
    overall_wink = compute_winkler(y_true, p10_all, p90_all)

    return {
        "label": label,
        "overall_mae": overall_mae,
        "overall_cov": overall_cov,
        "overall_winkler": overall_wink,
        "b1_overall_mae": b1_mae,
        "1h": h1,
        "3h": h3,
        "6h": h6,
    }


def train_candidate(
    label: str,
    db: Database,
    lambda_decay: float,
    window_days: Optional[int],
    save_dir: Path,
) -> dict:
    """Train 6 LightGBM models for a candidate config."""
    from ml.snapshots import SnapshotGenerator
    save_dir.mkdir(parents=True, exist_ok=True)
    sg = SnapshotGenerator(db)

    # Determine training window
    if window_days is not None:
        start_date = (datetime.date.fromisoformat(TRAIN_CUTOFF)
                      - datetime.timedelta(days=window_days - 1)).strftime("%Y-%m-%d")
    else:
        with db.transaction() as cur:
            cur.execute("SELECT MIN(run_date) as mn FROM station_events")
            row = cur.fetchone()
        start_date = row["mn"] if row and row["mn"] else "2025-02-08"

    print(f"\n[{label}] Training window: {start_date} -> {TRAIN_CUTOFF}  lambda={lambda_decay:.4f}")
    t0 = time.perf_counter()
    train_df = sg.build_dataset(start_date, TRAIN_CUTOFF, TRAIN_CUTOFF)
    print(f"[{label}] Train rows: {len(train_df):,}")

    # Compute time-decay weights
    if lambda_decay > 0.0 and "run_date" in train_df.columns:
        max_d = pd.to_datetime(train_df["run_date"]).max()
        days_diff = (max_d - pd.to_datetime(train_df["run_date"])).dt.days.values
        weights = np.exp(-lambda_decay * days_diff)
        ess = float((weights.sum() ** 2) / (weights ** 2).sum())
        print(f"[{label}] ESS (lambda={lambda_decay:.4f}): {ess:,.0f}")
    else:
        weights = None
        print(f"[{label}] No time decay (flat weights)")

    direct_mask = train_df["hops_remaining"] <= settings.DIRECT_MODEL_MAX_HOPS
    direct_df = train_df[direct_mask].copy()
    direct_w = weights[direct_mask] if weights is not None else None

    params_base = {
        "num_leaves": settings.LGBM_NUM_LEAVES,
        "learning_rate": settings.LGBM_LEARNING_RATE,
        "min_child_samples": settings.LGBM_MIN_CHILD_SAMPLES,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbosity": -1,
        "force_col_wise": True,
    }

    # Train 6 models
    for mtype, df_use, w_use, target in [
        ("direct", direct_df, direct_w, "target_direct_delay"),
        ("delta",  train_df,  weights,  "target_section_delta"),
    ]:
        for q in [0.1, 0.5, 0.9]:
            name = f"model_{mtype}_q{int(q*100)}"
            params = {**params_base, "objective": "quantile", "alpha": q}
            dtrain = lgb.Dataset(df_use[FEATURE_NAMES], label=df_use[target], weight=w_use)
            booster = lgb.train(params, dtrain, num_boost_round=settings.LGBM_N_ESTIMATORS)
            booster.save_model(str(save_dir / f"{name}.txt"))
            print(f"  [{label}] {name}: iter={booster.best_iteration or settings.LGBM_N_ESTIMATORS}")

    wall_time = time.perf_counter() - t0
    print(f"[{label}] Train wall-time: {wall_time:.1f}s")
    return {"label": label, "wall_time_s": wall_time, "train_rows": len(train_df),
            "start_date": start_date}


def run_shootout():
    db = get_db()
    sg = SnapshotGenerator(db)

    print("=" * 70)
    print("CANDIDATE SHOOTOUT — TASK-2 (19_RECOVERY)")
    print(f"Test window: {TEST_START} -> {TEST_END}  (cutoff={TRAIN_CUTOFF})")
    print("=" * 70)

    # Load test set ONCE — identical for all candidates
    print("\n[TEST] Loading test set...")
    test_df = sg.build_dataset(TEST_START, TEST_END, TRAIN_CUTOFF)
    print(f"[TEST] Rows: {len(test_df):,}")

    results = []

    # C0: git-restored artifacts (evaluate only, no training)
    print("\n--- C0: Git-restored (pre-regression, ef464a6) ---")
    c0_metrics_path = ARTIFACTS_DIR / "candidate0_metrics.json"
    if c0_metrics_path.exists():
        with open(c0_metrics_path, "r", encoding="utf-8-sig") as f:
            c0m = json.load(f)
        # C0 was evaluated on a slightly different test set (29,400 rows vs 25,203)
        # Re-evaluate on CURRENT test_df using C0's model files if they exist in a backup dir
        c0_dir = ARTIFACTS_DIR / "candidate0"
        if c0_dir.exists():
            c0_res = evaluate_models_on_test(test_df, c0_dir, "C0(git-restored)")
        else:
            # Use stored numbers from git (different test window — note this)
            c0_res = {
                "label": "C0(git-stored-diff-window)",
                "overall_mae": c0m["overall_mae"],
                "overall_cov": c0m.get("overall_coverage_80", 86.8),
                "overall_winkler": c0m.get("overall_winkler_score", 58.3),
                "b1_overall_mae": None,
                "1h": {"mae": c0m["metrics_by_horizon"]["1 h (<=90km)"]["mae_railtwin"],
                       "cov": c0m["metrics_by_horizon"]["1 h (<=90km)"]["coverage_80_percent"],
                       "winkler": c0m["metrics_by_horizon"]["1 h (<=90km)"]["winkler_score"],
                       "n": c0m["metrics_by_horizon"]["1 h (<=90km)"]["n_samples"]} if "metrics_by_horizon" in c0m else None,
                "3h": {"mae": c0m["metrics_by_horizon"]["3 h (90-250km)"]["mae_railtwin"],
                       "cov": c0m["metrics_by_horizon"]["3 h (90-250km)"]["coverage_80_percent"],
                       "winkler": c0m["metrics_by_horizon"]["3 h (90-250km)"]["winkler_score"],
                       "n": c0m["metrics_by_horizon"]["3 h (90-250km)"]["n_samples"]} if "metrics_by_horizon" in c0m else None,
                "6h": {"mae": c0m["metrics_by_horizon"]["6 h (>250km)"]["mae_railtwin"],
                       "cov": c0m["metrics_by_horizon"]["6 h (>250km)"]["coverage_80_percent"],
                       "winkler": c0m["metrics_by_horizon"]["6 h (>250km)"]["winkler_score"],
                       "n": c0m["metrics_by_horizon"]["6 h (>250km)"]["n_samples"]} if "metrics_by_horizon" in c0m else None,
                "note": "DIFFERENT TEST WINDOW (29,400 rows vs 25,203 — pre-spatial-fix era)",
            }
        results.append(c0_res)
    else:
        print("  [SKIP] candidate0_metrics.json not found")

    # C1: Last 30 days, no decay
    c1_dir = ARTIFACTS_DIR / "candidate1"
    info = train_candidate("C1(30d-flat)", db, 0.0, 30, c1_dir)
    c1_res = evaluate_models_on_test(test_df, c1_dir, "C1(30d-flat)")
    c1_res["train_info"] = info
    results.append(c1_res)

    # C2: Full archive, half-life 7d (lambda = ln2/7 ≈ 0.099)
    c2_dir = ARTIFACTS_DIR / "candidate2"
    info = train_candidate("C2(full+hl7d)", db, 0.0990, None, c2_dir)
    c2_res = evaluate_models_on_test(test_df, c2_dir, "C2(full+hl7d)")
    c2_res["train_info"] = info
    results.append(c2_res)

    # C3: Full archive, half-life 14d (lambda = ln2/14 ≈ 0.0495)
    c3_dir = ARTIFACTS_DIR / "candidate3"
    info = train_candidate("C3(full+hl14d)", db, 0.0495, None, c3_dir)
    c3_res = evaluate_models_on_test(test_df, c3_dir, "C3(full+hl14d)")
    c3_res["train_info"] = info
    results.append(c3_res)

    # --- Print comparison table ---
    print("\n" + "=" * 90)
    print("CANDIDATE COMPARISON TABLE (Test: {} -> {}, {} rows)".format(TEST_START, TEST_END, len(test_df)))
    print("=" * 90)
    print(f"{'Candidate':<22} {'Overall':>8} {'1h MAE':>8} {'1h Cov':>7} {'3h MAE':>8} {'3h Cov':>7} {'6h MAE':>8} {'6h Cov':>7} {'WallT':>7}")
    print("-" * 90)
    for r in results:
        h1 = r.get("1h") or {}
        h3 = r.get("3h") or {}
        h6 = r.get("6h") or {}
        note = " *" if r.get("note") else ""
        print(f"{r['label']:<22}{note} {r['overall_mae']:>7.2f}  {h1.get('mae',0):>7.2f}  {h1.get('cov',0):>6.1f}%  {h3.get('mae',0):>7.2f}  {h3.get('cov',0):>6.1f}%  {h6.get('mae',0):>7.2f}  {h6.get('cov',0):>6.1f}%  {r.get('train_info',{}).get('wall_time_s',0):>6.0f}s")
    print("=" * 90)
    print("* C0 evaluated on DIFFERENT test window (pre-spatial-fix era, 29k rows) — for reference only")

    # Determine winner (exclude C0 since different test window)
    candidates_eval = [r for r in results if "note" not in r and "error" not in r]
    if not candidates_eval:
        print("[ERROR] No valid candidates to compare — all errored")
        return results

    winner = min(candidates_eval, key=lambda r: (r["overall_mae"], r.get("1h", {}).get("mae", 999)))
    print(f"\n[DECISION] WINNER = {winner['label']}  (overall MAE={winner['overall_mae']:.2f}, 1h MAE={winner.get('1h',{}).get('mae',999):.2f})")
    print(f"[DECISION] Copy winner models to {ARTIFACTS_DIR}...")

    # Save shootout results
    shootout_path = ARTIFACTS_DIR / "shootout_results.json"
    with open(shootout_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[SAVED] Shootout results -> {shootout_path}")

    return results, winner


if __name__ == "__main__":
    results, winner = run_shootout()
    print(f"\n[SHOOTOUT DONE] Winner: {winner['label']}")
