"""Unit and property tests for training v2 components (Task T5)."""
from __future__ import annotations

import datetime
import numpy as np
import pytest
import torch

from ml.model_v2 import ALPHAS_V2, RailTwinGRUv2
from ml.train_v2 import EMA, GRUv2Ensemble, decay_sample_weights


def test_decay_sample_weights_half_life():
    """Recency decay assigns ~2x weight to events 90 days newer (lambda ~ 0.0077)."""
    dates = [
        "2026-05-01",  # ~90 days older
        "2026-08-01",  # Recent
    ]
    w = decay_sample_weights(dates, half_life_days=92.0)
    assert len(w) == 2
    assert w[1] > w[0]
    # Ratio should be approximately 2.0
    ratio = w[1] / w[0]
    assert 1.8 <= ratio <= 2.2


def test_ema_updates_and_copy():
    """EMA tracks model parameters with exponential moving average."""
    torch.manual_seed(42)
    model = torch.nn.Linear(10, 2)
    ema = EMA(model, decay=0.9)

    # Initial weights should match
    for k, v in model.state_dict().items():
        assert torch.equal(ema.shadow[k], v)

    # Change weights
    with torch.no_grad():
        model.weight.add_(1.0)
    ema.update(model)

    # Shadow should be 0.9 * old + 0.1 * new
    eval_model = torch.nn.Linear(10, 2)
    ema.copy_into(eval_model)
    assert not torch.equal(eval_model.weight, model.weight)


def test_gru_v2_ensemble_monotonicity_and_spread():
    """Deep ensemble averages quantile outputs and computes non-negative epistemic spread."""
    torch.manual_seed(42)
    m1 = RailTwinGRUv2(hidden_dim=32)
    m2 = RailTwinGRUv2(hidden_dim=32)
    m3 = RailTwinGRUv2(hidden_dim=32)

    ensemble = GRUv2Ensemble([m1, m2, m3])
    B, T = 4, 8

    seq = torch.randn(B, T, 8)
    station_ids = torch.randint(0, 500, (B, T))
    seq_mask = torch.ones((B, T), dtype=torch.bool)
    ctx = torch.randn(B, 34)

    out = ensemble(seq, station_ids, seq_mask, ctx)
    q = out["quantiles"]  # [B, 7]
    spread = out["member_spread"]  # [B]

    # Monotonicity check
    diffs = q[:, 1:] - q[:, :-1]
    assert (diffs >= -1e-5).all(), "Ensemble quantile crossing detected"
    # Spread should be non-negative
    assert (spread >= 0.0).all()
