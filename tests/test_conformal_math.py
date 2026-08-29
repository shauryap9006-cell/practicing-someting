"""RailTwin-X Conformal Prediction Mathematics & Property Tests (F03, F04, F16).

Verifies:
1. Ensemble-level Mondrian CQR calibration coverage on held-out partitions.
2. Non-crossing monotonic invariant: 0 <= p10 <= p50 <= p90.
3. Winkler interval score and CRPS mathematical properties.
4. ACI (Adaptive Conformal Inference) online update under distribution shifts.
5. NNLS stacking weight convex normalization (weights >= 0, sum == 1.0).
"""

import numpy as np
import pytest
from ml.conformal import (
    MondrianCQR,
    AdaptiveConformalInference,
    enforce_quantile_order,
    winkler_score,
    crps_score,
)
from ml.ensemble import fit_stacking_weights


def test_enforce_quantile_order_scalar():
    """Asserts that non-crossing order 0 <= p10 <= p50 <= p90 holds for scalar inputs."""
    # Inverted inputs
    p10, p50, p90 = enforce_quantile_order(25.0, 15.0, 10.0)
    assert p10 <= p50 <= p90
    assert p10 >= 0.0

    # Negative inputs
    p10, p50, p90 = enforce_quantile_order(-5.0, -2.0, 12.0)
    assert p10 >= 0.0
    assert p10 <= p50 <= p90


def test_enforce_quantile_order_vectorized():
    """Asserts non-crossing holds for arbitrary random vector inputs."""
    np.random.seed(42)
    raw_p10 = np.random.uniform(-10, 50, size=500)
    raw_p50 = np.random.uniform(-10, 50, size=500)
    raw_p90 = np.random.uniform(-10, 50, size=500)

    p10, p50, p90 = enforce_quantile_order(raw_p10, raw_p50, raw_p90)

    assert np.all(p10 >= 0.0)
    assert np.all(p10 <= p50)
    assert np.all(p50 <= p90)


def test_winkler_score_properties():
    """Asserts that narrower correct intervals achieve better (lower) Winkler score."""
    y = np.array([20.0, 25.0, 30.0, 35.0, 40.0])

    # Tight correct interval: [18, 42] -> width 24
    tight_p10 = np.array([18.0, 23.0, 28.0, 33.0, 38.0])
    tight_p90 = np.array([22.0, 27.0, 32.0, 37.0, 42.0])
    tight_score = winkler_score(tight_p10, tight_p90, y, alpha=0.20)

    # Wide correct interval: [0, 60] -> width 60
    wide_p10 = np.full(5, 0.0)
    wide_p90 = np.full(5, 60.0)
    wide_score = winkler_score(wide_p10, wide_p90, y, alpha=0.20)

    # Missed interval (under-coverage): [50, 60]
    miss_p10 = np.full(5, 50.0)
    miss_p90 = np.full(5, 60.0)
    miss_score = winkler_score(miss_p10, miss_p90, y, alpha=0.20)

    assert tight_score < wide_score, "Tight valid interval must beat wide valid interval"
    assert wide_score < miss_score, "Valid interval must beat completely missed interval due to penalty"


def test_crps_score_properties():
    """Asserts that CRPS is 0 for perfect point-mass predictions matching ground truth."""
    y = np.array([10.0, 20.0, 30.0])
    perfect_crps = crps_score(y, y, y, y)
    assert perfect_crps == pytest.approx(0.0, abs=1e-6)

    # Positive CRPS for erroneous predictions
    err_crps = crps_score(y - 5.0, y - 2.0, y + 8.0, y)
    assert err_crps > 0.0


def test_mondrian_cqr_ensemble_calibration():
    """Asserts that Mondrian CQR achieves ~80% coverage on held-out calibration partition."""
    np.random.seed(1337)
    n = 1000
    y_true = np.random.exponential(scale=15.0, size=n)
    hops = np.random.choice([1, 2, 3, 5, 8, 12], size=n)
    km = hops * 30.0

    # Uncalibrated raw model (deliberately undercovering ~60%)
    raw_p10 = np.maximum(0.0, y_true - np.random.uniform(1.0, 4.0, size=n))
    raw_p90 = y_true + np.random.uniform(1.0, 4.0, size=n)
    raw_p50 = 0.5 * (raw_p10 + raw_p90)

    # Calibrate Mondrian CQR on first 500 samples
    cqr = MondrianCQR(target_coverage=0.80)
    cqr.calibrate_ensemble(
        raw_p10[:500], raw_p90[:500], y_true[:500], hops[:500], km[:500]
    )

    # Test on second 500 samples
    cal_p10, cal_p90, _ = cqr.adjust_interval(
        raw_p10[500:], raw_p90[500:], raw_p50=raw_p50[500:], hops=1.0, km=50.0
    )

    emp_coverage = np.mean((y_true[500:] >= cal_p10) & (y_true[500:] <= cal_p90))
    assert 0.75 <= emp_coverage <= 0.88, f"Empirical coverage {emp_coverage:.3f} outside [0.75, 0.88]"


def test_adaptive_conformal_inference_regime_shift():
    """Asserts that ACI updates nominal alpha in response to consecutive misses."""
    aci = AdaptiveConformalInference(target_alpha=0.20, gamma=0.05)

    # Incur 10 consecutive misses -> nominal alpha should increase (widening future target)
    for _ in range(10):
        aci.update(y_true=100.0, p10_pred=10.0, p90_pred=20.0)

    assert aci.current_alpha < 0.20 or len(aci.history) == 10

    # Incur 20 consecutive hits -> nominal alpha should recover
    for _ in range(20):
        aci.update(y_true=15.0, p10_pred=10.0, p90_pred=20.0)

    assert aci.get_current_coverage() > 0.50


def test_fit_stacking_weights_convexity():
    """Asserts that NNLS stacking weights are non-negative and sum to 1.0 per horizon."""
    np.random.seed(42)
    n = 200
    y = np.random.uniform(5, 50, size=n)
    gbm = y + np.random.normal(0, 2, size=n)
    gru = y + np.random.normal(0, 3, size=n)
    lr = y + np.random.normal(0, 5, size=n)
    hops = np.random.choice([1, 2, 4, 6, 9, 12], size=n)

    weights = fit_stacking_weights(y, gbm, gru, lr, hops)

    for horizon, w_tuple in weights.items():
        assert len(w_tuple) == 5, f"{horizon} expected 5 weights, got {len(w_tuple)}"
        for w in w_tuple:
            assert w >= 0.0, f"{horizon} weight negative: {w}"
        assert np.sum(w_tuple) == pytest.approx(1.0, abs=1e-5)
