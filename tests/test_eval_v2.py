"""Unit tests for ml/evaluate_v2.py evaluation metrics and blocked splits (Task T3 + Bug 1, 2, 4 fixes)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.evaluate_v2 import (
    pinball,
    empirical_crps,
    winkler,
    randomized_pit,
    pit_histogram,
    diebold_mariano,
    corridor_fog_days,
    blocked_fog_holdout,
    to_common_grid,
    crps_grid,
)


def test_pinball_loss_exact_values():
    """Pinball loss matches definition max(alpha * err, (alpha - 1) * err)."""
    y = np.array([10.0, 5.0])
    q = np.array([[8.0, 10.0, 12.0], [4.0, 5.0, 7.0]])
    alphas = (0.1, 0.5, 0.9)

    loss = pinball(y, q, alphas)
    assert loss.shape == (2, 3)
    assert np.isclose(loss[0, 0], 0.2)
    assert np.isclose(loss[0, 1], 0.0)
    assert np.isclose(loss[0, 2], 0.2)


def test_empirical_crps_grid_interpolation():
    """CRPS uses common 49-point quadrature grid for non-negative metric."""
    y = np.array([10.0, 20.0])
    q = np.array([[10.0, 10.0, 10.0], [20.0, 20.0, 20.0]])
    alphas = (0.1, 0.5, 0.9)

    crps_val = empirical_crps(y, q, alphas)
    assert np.isclose(crps_val, 0.0)


def test_winkler_score():
    """Winkler score penalizes intervals that miss true targets."""
    y = np.array([10.0, 15.0])
    lo = np.array([5.0, 5.0])
    hi = np.array([12.0, 12.0])  # y[1]=15 is outside [5, 12]

    w_val = winkler(y, lo, hi, alpha=0.10)
    assert np.isclose(w_val, 37.0)


def test_randomized_pit_histogram():
    """Randomized PIT avoids discrete target atomicity."""
    rng = np.random.RandomState(42)
    n = 500
    y = rng.normal(10.0, 2.0, size=n)
    alphas = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
    q = np.array([np.quantile(y, alphas) for _ in range(n)])

    counts, edges, p_val = pit_histogram(y, q, alphas, bins=10, randomize=True)
    assert counts.sum() == n
    assert len(edges) == 11
    assert edges[0] == 0.0 and edges[-1] == 1.0


def test_diebold_mariano_paired_comparison():
    """DM test correctly identifies statistically superior forecasts."""
    n = 200
    rng = np.random.RandomState(42)
    e_bad = rng.normal(5.0, 1.0, size=n)
    e_good = rng.normal(1.0, 1.0, size=n)

    z, p = diebold_mariano(e_bad, e_good, lag=5)
    assert z > 3.0
    assert p < 0.001


def test_corridor_fog_days_and_blocked_holdout():
    """Blocked holdout creates 100% disjoint train and fog-test sets (Bug 1)."""
    dates = [f"2026-08-{i:02d}" for i in range(1, 29)]
    fog_days_set = {f"2026-08-{i:02d}" for i in [5, 6, 12, 13, 19, 20, 26, 27]}

    train_d, test_d = blocked_fog_holdout(dates, fog_days_set, buffer_days=1)
    assert len(set(train_d) & set(test_d)) == 0
    assert len(set(train_d) | set(test_d)) == len(dates)
    # Check buffer inclusion
    assert "2026-08-04" in test_d  # buffer around 2026-08-05
    assert "2026-08-05" in test_d
    assert "2026-08-06" in test_d
    assert "2026-08-07" in test_d  # buffer around 2026-08-06
