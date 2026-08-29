"""Comprehensive Unit & Adversarial Test Suite for Safety Interlock Layer (Phase G4).

Requires 100% coverage of safety/interlock.py with zero ML dependencies.
Tests cover:
- Red-line inputs: NaN, Inf, negative distance, extreme delay underflow
- Kinematic recovery violations (attempting 400 km/h recovery)
- Quantile crossing (q10 > q50, q50 > q90)
- Excessive uncertainty width (> 180 min)
- Hard delay boundaries (exceeding [-5, 720] min)
- Monotonic horizon drift (> 720 min)
- Master interlock pipeline and clamping reports
"""

import math
import pytest
from safety.interlock import (
    CheckResult,
    SafetyInterlockReport,
    check_input_sanity,
    check_recovery_feasibility,
    check_quantile_order,
    check_delay_bounds,
    check_monotonic_horizon,
    validate_prediction_through_interlock,
)


# ==============================================================================
# 1. INPUT SANITY TESTS (5 cases)
# ==============================================================================

def test_input_sanity_healthy():
    feats = {"current_delay": 15.0, "km_remaining": 80.0, "hops_remaining": 2, "speed": 100.0}
    res = check_input_sanity(feats)
    assert res.passed is True
    assert res.code == "OK_INPUT_VALID"


def test_input_sanity_missing_required():
    feats = {"current_delay": 15.0}  # missing km_remaining and hops_remaining
    res = check_input_sanity(feats)
    assert res.passed is False
    assert res.code == "ERR_MISSING_FEATURE"


def test_input_sanity_nan_values():
    feats = {"current_delay": float("nan"), "km_remaining": 50.0, "hops_remaining": 1}
    res = check_input_sanity(feats)
    assert res.passed is False
    assert res.code == "ERR_NON_FINITE_INPUT"


def test_input_sanity_infinite_values():
    feats = {"current_delay": 10.0, "km_remaining": float("inf"), "hops_remaining": 1}
    res = check_input_sanity(feats)
    assert res.passed is False
    assert res.code == "ERR_NON_FINITE_INPUT"


def test_input_sanity_negative_delay_underflow():
    feats = {"current_delay": -999.0, "km_remaining": 50.0, "hops_remaining": 1}
    res = check_input_sanity(feats)
    assert res.passed is False
    assert res.code == "ERR_DELAY_UNDERFLOW"


def test_input_sanity_negative_distance():
    feats = {"current_delay": 5.0, "km_remaining": -45.0, "hops_remaining": 1}
    res = check_input_sanity(feats)
    assert res.passed is False
    assert res.code == "ERR_NEGATIVE_DISTANCE"


# ==============================================================================
# 2. RECOVERY FEASIBILITY TESTS (4 cases)
# ==============================================================================

def test_recovery_feasibility_no_recovery():
    # Train is delayed by 20m, predicted delay is 25m (getting worse, feasible)
    res = check_recovery_feasibility(current_delay=20.0, predicted_delay=25.0, distance_km=50.0)
    assert res.passed is True
    assert res.code == "OK_NO_RECOVERY_OVERREACH"


def test_recovery_feasibility_normal_plausible_recovery():
    # Train is delayed by 30m, predicted delay is 26m over 50 km (4m recovery, feasible)
    res = check_recovery_feasibility(current_delay=30.0, predicted_delay=26.0, distance_km=50.0)
    assert res.passed is True
    assert res.code == "OK_RECOVERY_FEASIBLE"


def test_recovery_feasibility_impossible_recovery():
    # Train is delayed by 90m, model predicts 0m delay over 10km (impossible 800 km/h recovery)
    res = check_recovery_feasibility(current_delay=90.0, predicted_delay=0.0, distance_km=10.0, max_speed_kmph=110.0)
    assert res.passed is False
    assert res.code == "ERR_UNFEASIBLE_SPEED_RECOVERY"
    assert res.clamped_value is not None
    assert res.clamped_value > 0.0


def test_recovery_feasibility_zero_current_delay():
    res = check_recovery_feasibility(current_delay=0.0, predicted_delay=0.0, distance_km=100.0)
    assert res.passed is True


# ==============================================================================
# 3. QUANTILE ORDER TESTS (4 cases)
# ==============================================================================

def test_quantile_order_clean_monotonic():
    res, (q10, q50, q90) = check_quantile_order(p10=10.0, p50=15.0, p90=25.0)
    assert res.passed is True
    assert res.code == "OK_QUANTILE_MONOTONIC"
    assert (q10, q50, q90) == (10.0, 15.0, 25.0)


def test_quantile_order_crossing_p10_greater_than_p50():
    # Adversarial: model predicts p10=20m, p50=12m, p90=30m
    res, (q10, q50, q90) = check_quantile_order(p10=20.0, p50=12.0, p90=30.0)
    assert res.passed is False
    assert res.code == "ERR_QUANTILE_CROSSING"
    assert q10 <= q50 <= q90


def test_quantile_order_crossing_p50_greater_than_p90():
    # Adversarial: model predicts p10=5m, p50=40m, p90=30m
    res, (q10, q50, q90) = check_quantile_order(p10=5.0, p50=40.0, p90=30.0)
    assert res.passed is False
    assert res.code == "ERR_QUANTILE_CROSSING"
    assert q10 <= q50 <= q90


def test_quantile_order_excessive_width():
    # Adversarial: model predicts p10=0m, p50=50m, p90=250m (width 250 > 180 cap)
    res, (q10, q50, q90) = check_quantile_order(p10=0.0, p50=50.0, p90=250.0)
    assert res.passed is False
    assert res.code == "ERR_EXCESSIVE_QUANTILE_WIDTH"
    assert (q90 - q10) <= 180.0


# ==============================================================================
# 4. DELAY BOUNDS TESTS (3 cases)
# ==============================================================================

def test_delay_bounds_nominal():
    res, (q10, q50, q90) = check_delay_bounds(p10=0.0, p50=20.0, p90=45.0)
    assert res.passed is True
    assert res.code == "OK_WITHIN_BOUNDS"


def test_delay_bounds_negative_underflow():
    res, (q10, q50, q90) = check_delay_bounds(p10=-50.0, p50=-10.0, p90=5.0)
    assert res.passed is False
    assert res.code == "ERR_DELAY_OUT_OF_BOUNDS"
    assert q10 >= -5.0


def test_delay_bounds_upper_overflow():
    res, (q10, q50, q90) = check_delay_bounds(p10=700.0, p50=800.0, p90=900.0)
    assert res.passed is False
    assert res.code == "ERR_DELAY_OUT_OF_BOUNDS"
    assert q90 <= 720.0


# ==============================================================================
# 5. MONOTONIC HORIZON TESTS (2 cases)
# ==============================================================================

def test_monotonic_horizon_valid_drift():
    res = check_monotonic_horizon(current_delay=30.0, predicted_delay=90.0)
    assert res.passed is True
    assert res.code == "OK_HORIZON_DRIFT_VALID"


def test_monotonic_horizon_extreme_drift():
    # 800 minutes sudden delay shock
    res = check_monotonic_horizon(current_delay=10.0, predicted_delay=850.0)
    assert res.passed is False
    assert res.code == "ERR_EXCESSIVE_HORIZON_DRIFT"
    assert res.clamped_value is not None


# ==============================================================================
# 6. MASTER VALIDATOR INTEGRATION TESTS (5 cases)
# ==============================================================================

def test_master_interlock_clean_pass():
    feats = {"current_delay": 12.0, "km_remaining": 120.0, "hops_remaining": 3}
    report = validate_prediction_through_interlock(
        features=feats,
        raw_p10=10.0,
        raw_p50=15.0,
        raw_p90=25.0,
        base_tier="HIGH",
    )
    assert report.all_passed is True
    assert report.clamp_applied is False
    assert report.tier_downgrade is False
    assert report.confidence_tier == "HIGH"
    assert report.verify_with_controller is False
    assert report.human_ack_required is True


def test_master_interlock_adversarial_nan():
    feats = {"current_delay": float("nan"), "km_remaining": 120.0, "hops_remaining": 3}
    report = validate_prediction_through_interlock(
        features=feats,
        raw_p10=10.0,
        raw_p50=15.0,
        raw_p90=25.0,
    )
    assert report.all_passed is False
    assert report.tier_downgrade is True
    assert report.confidence_tier == "LOW"
    assert report.verify_with_controller is True


def test_master_interlock_adversarial_recovery():
    # 100m delay to 0m in 5km (impossible)
    feats = {"current_delay": 100.0, "km_remaining": 5.0, "hops_remaining": 1}
    report = validate_prediction_through_interlock(
        features=feats,
        raw_p10=0.0,
        raw_p50=0.0,
        raw_p90=5.0,
    )
    assert report.all_passed is False
    assert report.clamp_applied is True
    assert report.clamped_p50 > 50.0  # Must clamp to physically plausible value
    assert report.confidence_tier == "LOW"
    assert report.verify_with_controller is True


def test_master_interlock_adversarial_crossing_quantiles():
    feats = {"current_delay": 10.0, "km_remaining": 50.0, "hops_remaining": 2}
    report = validate_prediction_through_interlock(feats, raw_p10=30.0, raw_p50=15.0, raw_p90=10.0)
    assert report.all_passed is False
    assert report.clamp_applied is True
    assert report.clamped_p10 <= report.clamped_p50 <= report.clamped_p90


def test_master_interlock_adversarial_out_of_bounds():
    feats = {"current_delay": 10.0, "km_remaining": 50.0, "hops_remaining": 2}
    report = validate_prediction_through_interlock(feats, raw_p10=800.0, raw_p50=850.0, raw_p90=900.0)
    assert report.all_passed is False
    assert report.clamp_applied is True
    assert report.clamped_p90 <= 720.0


def test_master_interlock_adversarial_horizon_drift():
    feats = {"current_delay": -5.0, "km_remaining": 200.0, "hops_remaining": 4}
    report = validate_prediction_through_interlock(feats, raw_p10=700.0, raw_p50=720.0, raw_p90=720.0)
    assert report.all_passed is False
    assert report.clamp_applied is True
    assert report.clamped_p50 <= 720.0


def test_check_result_to_dict():
    res = CheckResult(name="test_check", passed=False, code="ERR_CODE", reason="test reason", clamped_value=12.5)
    d = res.to_dict()
    assert d["name"] == "test_check"
    assert d["passed"] is False
    assert d["code"] == "ERR_CODE"
    assert d["reason"] == "test reason"
    assert d["clamped_value"] == 12.5


def test_master_interlock_report_to_dict():
    feats = {"current_delay": 10.0, "km_remaining": 50.0, "hops_remaining": 2}
    report = validate_prediction_through_interlock(feats, 8.0, 12.0, 20.0)
    d = report.to_dict()
    assert "all_passed" in d
    assert "clamped_band" in d
    assert "human_ack_required" in d
    assert d["human_ack_required"] is True
    assert len(d["checks"]) == 5


def test_check_quantile_order_full_catches_mid_quantile_crossing():
    """check_quantile_order_full catches crossed intermediate quantiles (e.g. q25 > q50) (Bug 10)."""
    from safety.interlock import check_quantile_order_full
    # q10 <= q50 <= q90 is satisfied (5 <= 10 <= 20), but q25 = 12 > q50 = 10
    q_crossed = [2.0, 5.0, 12.0, 10.0, 15.0, 20.0, 25.0]
    res = check_quantile_order_full(q_crossed)
    assert res.passed is False
    assert res.code == "ERR_QUANTILE_VECTOR_CROSSING"

    # Strictly ordered 7-quantile vector passes
    q_valid = [2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0]
    res_valid = check_quantile_order_full(q_valid)
    assert res_valid.passed is True
    assert res_valid.code == "OK_QUANTILE_ORDER_FULL"

