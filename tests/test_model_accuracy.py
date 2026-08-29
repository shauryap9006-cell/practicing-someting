"""RailTwin-X Model Accuracy & Statistical Performance Regression Tests.

Ensures that refactoring or future feature development does not regress model accuracy,
conformal coverage, baseline superiority, or safety constraints.
"""

from __future__ import annotations

import numpy as np
import pytest
from ml.evaluate import Evaluator
from ml.snapshots import SnapshotGenerator
from safety.interlock import check_recovery_feasibility, validate_prediction_through_interlock


@pytest.fixture(scope="module")
def eval_summary():
    """Computes held-out evaluation summary once for all test assertions in module."""
    evaluator = Evaluator()
    return evaluator.evaluate_test_set()


def test_model_accuracy_regression(eval_summary):
    """Asserts that RailTwin-X achieves MAE < 10m on 1h horizon and overall MAE < 20m."""
    metrics = eval_summary.get("metrics_by_horizon", {})
    mae_1h = metrics.get("1 h (<=90km)", {}).get("mae_railtwin")
    assert mae_1h is not None, "Evaluation missing 1h horizon metrics"
    assert mae_1h < 10.0, f"1h Horizon MAE regressed: {mae_1h:.2f} min (Expected < 10.0 min)"

    overall_mae = eval_summary.get("overall_mae")
    assert overall_mae is not None, "Evaluation failed to compute overall MAE"
    assert overall_mae < 20.0, f"Overall MAE regressed: {overall_mae:.2f} min (Expected < 20.0 min)"


def test_conformal_coverage_bounds(eval_summary):
    """Asserts that empirical 80% confidence band coverage is within [70%, 98%]."""
    coverage = eval_summary.get("overall_coverage_80")
    assert coverage is not None, "Evaluation failed to compute overall coverage"
    assert 70.0 <= coverage <= 98.0, f"Conformal coverage out of bounds: {coverage:.1f}% (Expected 70-98%)"


def test_model_beats_official_baseline_b2(eval_summary):
    """Asserts that RailTwin-X outperforms Indian Railways official recovery baseline B2."""
    metrics = eval_summary.get("metrics_by_horizon", {})
    for horizon, vals in metrics.items():
        mae_rt = vals["mae_railtwin"]
        mae_b2 = vals["mae_b2"]
        assert mae_rt < mae_b2, f"Model failed to beat Baseline B2 in horizon {horizon}: Model={mae_rt:.2f}m vs B2={mae_b2:.2f}m"


def test_priority_dependent_recovery_interlock():
    """Asserts that safety interlock recovery check respects train priority."""
    # Priority 1 (Vande Bharat): 15 km/min -> over 30 km, can recover 30/15 + 3 = 5 min
    res_p1 = check_recovery_feasibility(
        current_delay=30.0,
        predicted_delay=25.5,
        distance_km=30.0,
        priority=1,
    )
    assert res_p1.passed is True, "Priority 1 train recovery within 5 min should pass"

    # Priority 4 (Freight): 40 km/min -> over 30 km, can recover 30/40 + 3 = 3.75 min
    res_p4 = check_recovery_feasibility(
        current_delay=30.0,
        predicted_delay=25.0,  # 5 min reduction > 3.75 min max feasible
        distance_km=30.0,
        priority=4,
    )
    assert res_p4.passed is False, "Priority 4 train recovery of 5 min over 30km should fail"
    assert res_p4.clamped_value is not None


def test_cancellation_likelihood_flag():
    """Asserts that delays > 300 minutes are flagged with cancellation likelihood."""
    rep_normal = validate_prediction_through_interlock(
        features={"current_delay": 50.0, "km_remaining": 100.0, "hops_remaining": 2, "train_priority": 2},
        raw_p10=40.0,
        raw_p50=50.0,
        raw_p90=70.0,
    )
    assert rep_normal.cancellation_likelihood is False

    rep_delayed = validate_prediction_through_interlock(
        features={"current_delay": 350.0, "km_remaining": 100.0, "hops_remaining": 2, "train_priority": 2},
        raw_p10=320.0,
        raw_p50=360.0,
        raw_p90=400.0,
    )
    assert rep_delayed.cancellation_likelihood is True
