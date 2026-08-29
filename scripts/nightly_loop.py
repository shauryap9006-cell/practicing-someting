"""RailTwin-X Automated Nightly Retraining, Drift & Evaluation Loop (F43, F44, F45).

Pipeline Steps:
1. Ingest & sanitize live telemetry (check constraints, range bounds, deduplication).
2. Run PSI & CUSUM drift monitors on recent scoring window.
3. Retrain LightGBM and PyTorch GRU challenger models.
4. Execute purged 3-way disjoint split cross-validation & Winkler / CRPS evaluation.
5. Update model registry & emit canonical metrics.json.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from data.db import get_db
from ml.drift import PSIDriftMonitor
from ml.evaluate import evaluate_test_set
from ml.model_seq import GRUChallengerTrainer
from ml.train import ModelTrainer


def run_nightly_pipeline() -> dict:
    """Executes the complete end-to-end nightly MLOps governance loop."""
    print("================================================================")
    print(f"[{datetime.datetime.now().isoformat()}] RailTwin-X Nightly MLOps Loop Starting")
    print("================================================================")

    db = get_db()
    db.ensure_indexes()
    mat_count = db.materialize_historical_baselines()
    print(f"[STAGE 1/5] Materialized {mat_count} historical baselines.")

    # 2. Drift Monitoring
    print("[STAGE 2/5] Running Population Stability & Drift Monitoring...")
    drift_mon = PSIDriftMonitor(db=db)
    drift_rep = drift_mon.run()
    drift_rep.save()
    print(f"[STAGE 2/5] Drift Status: {drift_rep.overall_status} (Monitored {drift_rep.total_features} features)")

    # 3. Retrain LightGBM Champion Models
    print("[STAGE 3/5] Training LightGBM Quantile Models...")
    trainer = ModelTrainer(db=db)
    train_summary = trainer.train_all()

    # 4. Retrain PyTorch GRU Challenger
    print("[STAGE 4/5] Training PyTorch GRU Challenger...")
    gru_trainer = GRUChallengerTrainer(db=db)
    gru_summary = gru_trainer.train(epochs=10)

    # 5. Evaluate on Held-Out Test Set & Update Canonical metrics.json
    print("[STAGE 5/5] Running Comprehensive Metrics-as-Code Evaluation...")
    eval_res = evaluate_test_set()

    print("================================================================")
    print(f"[{datetime.datetime.now().isoformat()}] Nightly Loop Completed Successfully!")
    print(f"  Champion Served: {eval_res.get('model_champion', 'PyTorch_GRU_Quantile')}")
    print(f"  Test MAE: {eval_res.get('test_mae', 0.0):.2f} min")
    print(f"  80% Coverage: {eval_res.get('coverage_80_pct', 0.0):.1f}%")
    print(f"  Winkler Score: {eval_res.get('winkler_score_80', 0.0):.2f}")
    print("================================================================")

    return {
        "status": "SUCCESS",
        "timestamp": datetime.datetime.now().isoformat(),
        "drift_status": drift_rep.overall_status,
        "evaluation": eval_res,
    }


if __name__ == "__main__":
    run_nightly_pipeline()
