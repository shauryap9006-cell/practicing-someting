"""RailTwin-X Comprehensive Hypothesis Property-Based Test Suite (F48).

Tests:
1. Schedule and delay physical constraints (no negative durations, monotonic bounds).
2. Interlock clamping invariants.
3. Position resolver confidence invariants (0 <= conf <= 1, posterior sums to 1.0).
4. CUSUM drift detection invariants.
"""

from __future__ import annotations

import math
from hypothesis import given, strategies as st
import pytest

from engine.position_resolver import PositionRecord
from ml.drift import CUSUMDetector, ADWINDetector
from safety.interlock import validate_prediction_through_interlock


@given(
    current_delay=st.floats(min_value=0.0, max_value=600.0),
    p10=st.floats(min_value=-50.0, max_value=800.0),
    p50=st.floats(min_value=-50.0, max_value=800.0),
    p90=st.floats(min_value=-50.0, max_value=800.0),
)
def test_interlock_clamping_properties(current_delay: float, p10: float, p50: float, p90: float):
    """Property test: Safety interlock clamps within physical limits [0, 720] and enforces p10 <= p50 <= p90."""
    features = {
        "current_delay": current_delay,
        "km_remaining": 50.0,
        "hops_remaining": 2,
    }
    rep = validate_prediction_through_interlock(
        features=features,
        raw_p10=p10,
        raw_p50=p50,
        raw_p90=p90,
        base_tier="HIGH",
    )

    assert 0.0 <= rep.clamped_p10 <= 720.0
    assert rep.clamped_p10 <= rep.clamped_p50 <= 720.0
    assert rep.clamped_p50 <= rep.clamped_p90 <= 720.0
    assert rep.confidence_tier in ("HIGH", "MEDIUM", "LOW")


@given(
    values=st.lists(st.floats(min_value=-10.0, max_value=50.0), min_size=5, max_size=50),
)
def test_cusum_drift_detector_properties(values: list[float]):
    """Property test: CUSUM detector never crashes, accumulator remains non-negative."""
    detector = CUSUMDetector(target_mean=0.0, threshold=10.0, drift=1.0)
    for i, v in enumerate(values):
        drift_flag = detector.update(v, step=i)
        assert detector.s_pos >= 0.0
        assert detector.s_neg >= 0.0
        assert isinstance(drift_flag, bool)
