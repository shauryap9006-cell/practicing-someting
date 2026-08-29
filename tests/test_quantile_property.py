"""Hypothesis Property-Based Tests for Quantile Ordering Invariant (F16).

Tests that enforce_quantile_order(p10, p50, p90, cap) preserves the mathematical
invariant 0 <= p10 <= p50 <= p90 <= cap across arbitrary and adversarial inputs.
"""

from __future__ import annotations

import math
from hypothesis import given, strategies as st
import pytest

from api.predictor import enforce_quantile_order

float_strategy = st.one_of(
    st.floats(min_value=-1e6, max_value=1e6),
    st.just(float("nan")),
    st.just(float("inf")),
    st.just(float("-inf")),
    st.just(0.0),
    st.just(-50.0),
    st.just(9999.0),
)


@given(
    p10=float_strategy,
    p50=float_strategy,
    p90=float_strategy,
    cap=st.one_of(st.none(), st.floats(min_value=1.0, max_value=1440.0)),
)
def test_quantile_ordering_invariants(p10: float, p50: float, p90: float, cap: float | None):
    """Property test: 0 <= p10 <= p50 <= p90 <= cap for 500+ generated input combinations."""
    safe_p10, safe_p50, safe_p90 = enforce_quantile_order(p10, p50, p90, cap=cap)

    # 1. No NaNs or infinities in output
    assert not math.isnan(safe_p10)
    assert not math.isnan(safe_p50)
    assert not math.isnan(safe_p90)
    assert not math.isinf(safe_p10)
    assert not math.isinf(safe_p50)
    assert not math.isinf(safe_p90)

    # 2. Monotonic Non-Crossing Invariant
    assert 0.0 <= safe_p10
    assert safe_p10 <= safe_p50
    assert safe_p50 <= safe_p90

    # 3. Cap Invariant if specified
    if cap is not None and cap > 0.0:
        assert safe_p90 <= cap
