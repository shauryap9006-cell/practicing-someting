#!/usr/bin/env python
"""RailTwin-X Nightly Pipeline Runner — Phase 7 (MLOps).

Orchestrates the full nightly data pipeline:
  1. Seed / refresh database (mixed network)
  2. Build snapshot cache
  3. Retrain LightGBM ensemble + per-horizon CQR
  4. Train / promote PyTorch GRU champion (Wilcoxon gate)
  5. Run held-out evaluation → metrics.json
  6. Run PSI drift monitor → drift_report.json
  7. Print pass/fail summary

Usage:
    python -m scripts.nightly_pipeline [--network=mixed] [--skip-seed]
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
import time
from pathlib import Path


def _run(cmd: list[str], label: str) -> bool:
    """Runs a subprocess command. Returns True on success."""
    start = time.perf_counter()
    print(f"\n{'='*60}")
    print(f"[STEP] {label}")
    print(f"  cmd: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        print(f"\n[FAIL] {label} failed (exit code {result.returncode}) in {elapsed:.1f}s")
        return False

    print(f"\n[OK]   {label} completed in {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(description="RailTwin-X Nightly Pipeline")
    parser.add_argument("--network", choices=["passenger", "dfc", "mixed"], default="mixed")
    parser.add_argument("--skip-seed", action="store_true", help="Skip database reseed step")
    parser.add_argument("--skip-gru", action="store_true", help="Skip PyTorch GRU training (faster)")
    args = parser.parse_args()

    py = sys.executable
    wall_start = time.perf_counter()
    results: dict[str, bool] = {}

    print(f"\n{'#'*60}")
    print(f"# RailTwin-X NIGHTLY PIPELINE — {datetime.datetime.now().isoformat()}")
    print(f"# Network: {args.network}")
    print(f"{'#'*60}")

    # 1. Seed database
    if not args.skip_seed:
        ok = _run([py, "-m", "data.seed", f"--network={args.network}"], "Database Seed")
        results["seed"] = ok
        if not ok:
            print("\n[ABORT] Seed failed — cannot proceed without fresh data.")
            sys.exit(1)
    else:
        print("\n[SKIP] Database seed (--skip-seed)")

    # 2. Build snapshot parquet cache
    ok = _run([py, "-c",
               "from ml.snapshots import SnapshotBuilder; "
               "from data.db import get_db; "
               "sb = SnapshotBuilder(get_db()); "
               "df = sb.build_snapshot_dataset(); "
               "print(f'Snapshots: {len(df):,} rows')"],
              "Snapshot Cache Build")
    results["snapshot"] = ok

    # 3. Retrain LightGBM ensemble + CQR
    ok = _run([py, "-m", "ml.train"], "LightGBM Ensemble Retrain")
    results["lgbm_train"] = ok

    # 4. Train GRU champion (skip with --skip-gru for speed)
    if not args.skip_gru:
        ok = _run([py, "-m", "ml.model_seq"], "PyTorch GRU Champion Train")
        results["gru_train"] = ok
    else:
        print("\n[SKIP] PyTorch GRU training (--skip-gru)")

    # 5. Ensemble promotion gate + generate manifest
    ok = _run([py, "-m", "ml.ensemble"], "Ensemble Promotion Gate (Wilcoxon)")
    results["ensemble"] = ok

    # 6. Held-out evaluation → metrics.json
    ok = _run([py, "-m", "ml.evaluate"], "Held-Out Evaluation (F14 Proof Table)")
    results["evaluate"] = ok

    # 7. PSI Drift Monitor → drift_report.json
    ok = _run([py, "-m", "ml.drift"], "PSI Drift Monitor")
    results["drift"] = ok

    # Summary
    wall_elapsed = time.perf_counter() - wall_start
    print(f"\n{'='*60}")
    print(f"NIGHTLY PIPELINE SUMMARY  (total: {wall_elapsed:.0f}s)")
    print(f"{'='*60}")
    all_ok = True
    for step, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon}  {step}")
        if not passed:
            all_ok = False

    if all_ok:
        print("\n[SUCCESS] All pipeline steps passed. System ready for inference.")
        sys.exit(0)
    else:
        print("\n[WARN] Some steps failed — check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
