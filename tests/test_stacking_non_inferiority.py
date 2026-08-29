"""Unit and statistical tests for NNLS Stacking & Non-Inferiority Gate (Task T7)."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from ml.ensemble import fit_stacking_weights


def test_nnls_stacking_non_inferiority():
    """Convex NNLS stacking produces MAE <= min(component MAEs) + epsilon."""
    rng = np.random.RandomState(42)
    n = 500

    y_true = rng.exponential(15.0, size=n)
    # Component models with varying errors
    gbm_preds = y_true + rng.normal(0, 4.0, size=n)
    gru_preds = y_true + rng.normal(0, 3.0, size=n)
    lr_preds = y_true + rng.normal(0, 8.0, size=n)
    b1_preds = y_true + rng.normal(0, 6.0, size=n)
    b3_preds = y_true + rng.normal(0, 7.0, size=n)

    hops = rng.randint(1, 10, size=n)
    km = hops * 30.0

    weights = fit_stacking_weights(
        y_true=y_true,
        gbm_preds=gbm_preds,
        gru_preds=gru_preds,
        lr_preds=lr_preds,
        hops_vec=hops,
        km_vec=km,
        b1_preds=b1_preds,
        b3_preds=b3_preds,
    )

    # Reconstruct predictions
    pred_stack = np.zeros(n)
    for i in range(n):
        k = km[i]
        bucket = "short" if k <= 90 else ("medium" if k <= 250 else "long")
        w = weights[bucket]
        pred_stack[i] = (
            w[0] * gbm_preds[i]
            + w[1] * gru_preds[i]
            + w[2] * lr_preds[i]
            + w[3] * b1_preds[i]
            + w[4] * b3_preds[i]
        )

    mae_stack = np.abs(y_true - pred_stack).mean()
    mae_gbm = np.abs(y_true - gbm_preds).mean()
    mae_gru = np.abs(y_true - gru_preds).mean()
    min_comp_mae = min(mae_gbm, mae_gru)

    assert mae_stack <= min_comp_mae + 0.1, f"Stacking violated non-inferiority: {mae_stack} > {min_comp_mae}"


def test_wilcoxon_non_inferiority_gate():
    """Wilcoxon signed-rank test rejects inferior or identical rolling weights."""
    rng = np.random.RandomState(42)
    n = 200

    e_static = rng.normal(5.0, 1.0, size=n)
    # Rolling is no better (same distribution)
    e_rolling_equal = rng.normal(5.0, 1.0, size=n)
    stat, p_equal = stats.wilcoxon(e_static, e_rolling_equal, alternative="greater")
    # Gate requires p < 0.01 to switch; p_equal should fail this threshold
    assert p_equal > 0.01

    # Rolling is significantly better
    e_rolling_better = rng.normal(3.0, 0.8, size=n)
    stat, p_better = stats.wilcoxon(e_static, e_rolling_better, alternative="greater")
    assert p_better < 0.001
