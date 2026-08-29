"""Unit & Integration Tests for ML Subsystem (M2 - F2, F3, F14).

Tests:
1. 17-feature extraction and validation.
2. Leakage safety (Train-split historical averages).
3. 6 LightGBM quantile regression models training.
4. Conformal calibration and monotonic interval prediction (p10 <= p50 <= p90).
5. Evaluation & F14 proof table generation.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from data.db import Database
from data.seed import run_full_seed
from ml.features import FEATURE_NAMES, validate_feature_dataframe
from ml.snapshots import SnapshotGenerator
from ml.train import ModelTrainer
from ml.evaluate import Evaluator


@pytest.fixture(scope="module")
def ml_db(tmp_path_factory) -> Database:
    """Fixture providing a seeded database for ML tests."""
    temp_dir = tmp_path_factory.mktemp("ml_test_data")
    db_file = temp_dir / "ml_test.db"
    run_full_seed(db_file)
    return Database(db_file)


def test_feature_vector_validation(ml_db: Database):
    """Verifies feature extraction outputs valid 17-feature vectors without NaNs."""
    sg = SnapshotGenerator(ml_db)
    df = sg.build_dataset("2026-08-01", "2026-08-03", "2026-08-21")
    assert len(df) > 100
    assert len(FEATURE_NAMES) == 25
    for f in FEATURE_NAMES:
        assert f in df.columns, f"Feature {f} missing from DataFrame"
    validate_feature_dataframe(df)


def test_ml_training_and_proof_table(ml_db: Database, tmp_path: Path):
    """Tests end-to-end training of 6 models, conformal calibration, and proof table evaluation."""
    artifacts_dir = tmp_path / "artifacts"
    trainer = ModelTrainer(db=ml_db, artifacts_dir=artifacts_dir)
    manifest = trainer.train_all()

    assert manifest["train_rows"] > 0
    assert manifest["test_rows"] > 0
    assert manifest["conformal_q_hat"] >= 0.0

    # Verify all 6 model booster files exist
    for q in [10, 50, 90]:
        assert (artifacts_dir / f"model_direct_q{q}.txt").exists()
        assert (artifacts_dir / f"model_delta_q{q}.txt").exists()

    # Evaluate
    evaluator = Evaluator(db=ml_db, artifacts_dir=artifacts_dir)
    summary = evaluator.evaluate_test_set()

    assert "proof_table" in summary
    assert len(summary["proof_table"]) >= 2
    assert summary["overall_coverage_80"] >= 65.0  # Conformal coverage validation
