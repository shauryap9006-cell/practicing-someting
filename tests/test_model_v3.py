"""Unit and property tests for RailTwinGRUv3 architecture and RegimeMoEHead (Phase D)."""
from __future__ import annotations

import pytest
import torch

from ml.model_v3 import (
    ALPHAS_V3,
    GRUv3Ensemble,
    MonotoneQuantileHead,
    PinballCRPSLoss,
    RailTwinGRUv3,
    RegimeMoEHead,
)


def test_monotone_quantile_head_strict_order():
    """Verifies that MonotoneQuantileHead produces strictly non-decreasing quantiles."""
    torch.manual_seed(42)
    head = MonotoneQuantileHead(hidden_dim=32, alphas=ALPHAS_V3)
    x = torch.randn(100, 32)
    q = head(x)  # [100, 7]

    diffs = q[:, 1:] - q[:, :-1]
    assert (diffs >= -1e-6).all(), "Quantile crossing detected in MonotoneQuantileHead"


def test_regime_moe_head_properties():
    """Verifies MoE quantile mixing: monotonicity, sum-to-1 gate weights, and finite aux loss."""
    torch.manual_seed(42)
    moe = RegimeMoEHead(hidden_dim=32, n_experts=3, gate_dim=6, alphas=ALPHAS_V3)

    h = torch.randn(50, 32)
    gate_ctx = torch.randn(50, 6)

    q, w, aux = moe(h, gate_ctx)

    # 1. Monotonicity by convex combination
    diffs = q[:, 1:] - q[:, :-1]
    assert (diffs >= -1e-6).all(), "MoE quantile crossing detected"

    # 2. Gate weights sum to 1.0
    w_sum = w.sum(dim=-1)
    assert torch.allclose(w_sum, torch.ones_like(w_sum), atol=1e-5), "Gate weights do not sum to 1"

    # 3. Finite aux loss
    assert torch.isfinite(aux), f"Aux loss is not finite: {aux}"
    assert aux.dim() == 0, "Aux loss must be a scalar"


def test_railtwin_gru_v3_forward():
    """Verifies complete RailTwinGRUv3 forward pass and tensor shapes."""
    torch.manual_seed(42)
    model = RailTwinGRUv3(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=24,
        nbr_feat_dim=12,
        hidden_dim=64,
        gru_layers=2,
        vocab_size=500,
        n_experts=3,
        gate_dim=6,
    )

    B, T = 4, 8
    seq = torch.randn(B, T, 8)
    station_ids = torch.randint(0, 500, (B, T))
    seq_mask = torch.ones((B, T), dtype=torch.bool)
    ctx = torch.randn(B, 24)

    out = model(seq=seq, station_ids=station_ids, seq_mask=seq_mask, ctx=ctx)

    assert "quantiles" in out
    assert "gate_weights" in out
    assert "aux_loss" in out
    assert out["quantiles"].shape == (B, 7)
    assert out["gate_weights"].shape == (B, 3)

    # Monotonicity check on full model
    diffs = out["quantiles"][:, 1:] - out["quantiles"][:, :-1]
    assert (diffs >= -1e-6).all(), "Full GRUv3 model quantile crossing detected"


def test_gru_v3_ensemble_monotonicity_and_spread():
    """Verifies GRUv3Ensemble output shape, monotonicity, and non-negative epistemic spread."""
    torch.manual_seed(42)
    m1 = RailTwinGRUv3(hidden_dim=32, vocab_size=200)
    m2 = RailTwinGRUv3(hidden_dim=32, vocab_size=200)
    m3 = RailTwinGRUv3(hidden_dim=32, vocab_size=200)

    ensemble = GRUv3Ensemble([m1, m2, m3])
    B, T = 8, 8

    seq = torch.randn(B, T, 8)
    station_ids = torch.randint(0, 200, (B, T))
    seq_mask = torch.ones((B, T), dtype=torch.bool)
    ctx = torch.randn(B, 24)

    out = ensemble(seq=seq, station_ids=station_ids, seq_mask=seq_mask, ctx=ctx)

    assert out["quantiles"].shape == (B, 7)
    assert (out["member_spread"] >= 0.0).all(), "Negative epistemic spread detected"

    diffs = out["quantiles"][:, 1:] - out["quantiles"][:, :-1]
    assert (diffs >= -1e-6).all(), "Ensemble quantile crossing detected"
