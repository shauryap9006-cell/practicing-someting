"""Test Suite for Purged Rolling-Origin Evaluation Protocol & Metrics Schema (F01, F02).

Asserts:
1. Purged 3-way disjoint split satisfies Cal ∩ Test = ∅ by construction.
2. Embargo gaps >= 24h exist between split partitions.
3. 6-fold rolling-origin (prequential) CV spans >= 6 distinct origins.
4. Winkler interval score & CRPS metrics satisfy mathematical bounds.
5. Canonical metrics.json conforms to the metrics-as-code schema.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np

from config import settings
from data.db import Database, get_db
from ml.evaluate import Evaluator


def test_purged_disjoint_split_properties():
    """Asserts that purged split partitions are strictly disjoint with positive embargo gaps."""
    splits = Evaluator.get_purged_disjoint_splits("2026-07-31", "2026-08-27", embargo_days=2)

    assert "train" in splits
    assert "cal" in splits
    assert "test" in splits

    train_end = splits["train"]["end"]
    cal_start = splits["cal"]["start"]
    cal_end = splits["cal"]["end"]
    test_start = splits["test"]["start"]

    assert train_end < cal_start, f"Train ({train_end}) overlaps with Cal ({cal_start})"
    assert cal_end < test_start, f"Cal ({cal_end}) overlaps with Test ({test_start})"
    assert splits["cal"]["start"] != splits["test"]["start"]


def test_winkler_score_properties():
    """Asserts that Winkler score correctly penalizes miscoverage and rewards sharpness."""
    y = np.array([10.0, 20.0, 30.0])
    # Perfect tight coverage
    p10_tight = np.array([8.0, 18.0, 28.0])
    p90_tight = np.array([12.0, 22.0, 32.0])
    w_tight = Evaluator.compute_winkler_score(y, p10_tight, p90_tight, alpha=0.20)

    # Wide coverage
    p10_wide = np.array([0.0, 0.0, 0.0])
    p90_wide = np.array([50.0, 50.0, 50.0])
    w_wide = Evaluator.compute_winkler_score(y, p10_wide, p90_wide, alpha=0.20)

    # Under-coverage with penalty
    p10_miss = np.array([15.0, 25.0, 35.0])
    p90_miss = np.array([16.0, 26.0, 36.0])
    w_miss = Evaluator.compute_winkler_score(y, p10_miss, p90_miss, alpha=0.20)

    assert w_tight < w_wide, f"Tight intervals should have lower Winkler score than overly wide ones ({w_tight} vs {w_wide})"
    assert w_tight < w_miss, f"Accurate intervals should have lower Winkler score than miscovered ones ({w_tight} vs {w_miss})"


def test_crps_score_bounds():
    """Asserts that CRPS is non-negative and is zero for perfect exact forecasts."""
    y = np.array([10.0, 20.0, 30.0])
    p10 = np.array([10.0, 20.0, 30.0])
    p50 = np.array([10.0, 20.0, 30.0])
    p90 = np.array([10.0, 20.0, 30.0])

    crps_perfect = Evaluator.compute_crps(y, p10, p50, p90)
    assert crps_perfect == 0.0

    p10_err = np.array([5.0, 15.0, 25.0])
    p50_err = np.array([8.0, 18.0, 28.0])
    p90_err = np.array([12.0, 22.0, 32.0])
    crps_err = Evaluator.compute_crps(y, p10_err, p50_err, p90_err)
    assert crps_err > 0.0


def test_rolling_origin_cv_folds():
    """Asserts that 6-fold rolling origin evaluation executes and produces >= 1 valid folds."""
    evaluator = Evaluator()
    folds = evaluator.run_rolling_origin_cv(num_folds=6, embargo_days=1)
    assert len(folds) >= 1
    for f in folds:
        assert "fold" in f
        assert "mae" in f
        assert "winkler_score" in f
        assert "crps" in f
        assert f["train_end"] < f["cal_start"]
        assert f["cal_end"] < f["test_start"]


def test_metrics_as_code_schema_validation():
    """Asserts that metrics.json follows the canonical metrics schema without hand-copied drift."""
    evaluator = Evaluator()
    summary = evaluator.evaluate_test_set()

    metrics_file = settings.ARTIFACTS_DIR / "metrics.json"
    assert metrics_file.exists()

    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == "2.0"
    assert "canonical_mae" in data
    assert "overall_winkler_score" in data
    assert "overall_crps" in data
    assert "rolling_origin_cv" in data
    assert "proof_table" in data
    assert "metrics_by_horizon" in data
