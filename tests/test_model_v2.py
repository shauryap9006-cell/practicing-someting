"""Unit and property-based tests for RailTwinGRUv2 architecture (Task T4)."""
from __future__ import annotations

import pytest
import torch
import numpy as np
from hypothesis import given, strategies as st, settings

from ml.model_v2 import (
    ALPHAS_V2,
    IDX_Q10,
    IDX_Q50,
    IDX_Q90,
    MonotoneQuantileHead,
    JourneyNorm,
    FiLM,
    RailTwinGRUv2,
    PinballCRPSLoss,
)


def test_monotone_quantile_head_ordering_random_inputs():
    """Property test: Head outputs are strictly non-decreasing across all quantile levels."""
    torch.manual_seed(42)
    head = MonotoneQuantileHead(hidden_dim=64, alphas=ALPHAS_V2)
    # Test on 200 random hidden vectors
    h = torch.randn(200, 64)
    q = head(h)  # [200, 7]

    diffs = q[:, 1:] - q[:, :-1]
    assert (diffs >= -1e-6).all(), "Monotone quantile ordering violated in MonotoneQuantileHead"


def test_railtwin_gru_v2_forward_and_legacy_view():
    """End-to-end forward pass produces valid monotone quantiles, attention weights, and legacy view."""
    torch.manual_seed(42)
    B, T, K = 4, 8, 8
    model = RailTwinGRUv2(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=34,
        nbr_feat_dim=12,
        hidden_dim=64,
        vocab_size=256,
    )

    seq = torch.randn(B, T, 8)
    station_ids = torch.randint(0, 256, (B, T))
    seq_mask = torch.ones((B, T), dtype=torch.bool)
    ctx = torch.randn(B, 34)
    nbr = torch.randn(B, K, 12)
    nbr_mask = torch.ones((B, K), dtype=torch.bool)

    out = model(seq, station_ids, seq_mask, ctx, nbr, nbr_mask)
    q = out["quantiles"]
    assert q.shape == (B, len(ALPHAS_V2))

    # Strict monotonicity
    diffs = q[:, 1:] - q[:, :-1]
    assert (diffs >= -1e-5).all(), "End-to-end forward pass produced crossing quantiles"

    # Legacy view mapping
    q10, q50, q90 = RailTwinGRUv2.legacy_view(q)
    assert q10.shape == (B,)
    assert q50.shape == (B,)
    assert q90.shape == (B,)
    assert (q10 <= q50 + 1e-5).all()
    assert (q50 <= q90 + 1e-5).all()


def test_gradient_flow_on_one_stop_journey():
    """Model supports 1-stop journey sequences (T=1) without vanishing or exploding gradients."""
    model = RailTwinGRUv2(
        seq_feat_dim=8,
        station_emb_dim=8,
        ctx_dim=34,
        nbr_feat_dim=12,
        hidden_dim=32,
        gru_layers=1,
    )
    criterion = PinballCRPSLoss()

    seq = torch.randn(2, 1, 8, requires_grad=True)
    station_ids = torch.tensor([[10], [20]], dtype=torch.long)
    seq_mask = torch.ones((2, 1), dtype=torch.bool)
    ctx = torch.randn(2, 34, requires_grad=True)
    target = torch.tensor([15.0, 25.0], dtype=torch.float32)

    out = model(seq, station_ids, seq_mask, ctx)
    loss, _ = criterion(out["quantiles"], target)
    loss.backward()

    assert seq.grad is not None
    assert ctx.grad is not None
    assert not torch.isnan(seq.grad).any()
    assert not torch.isnan(ctx.grad).any()


def test_journey_norm_masked_statistics():
    """JourneyNorm calculates mean and variance strictly on non-padded elements."""
    x = torch.tensor([
        [[10.0, 5.0], [20.0, 15.0], [0.0, 0.0]],
        [[30.0, 10.0], [0.0, 0.0], [0.0, 0.0]],
    ])  # [2, 3, 2]
    mask = torch.tensor([
        [True, True, False],
        [True, False, False],
    ])

    mu, sd = JourneyNorm.masked_stats(x, mask)
    assert mu.shape == (2, 2)
    assert np.isclose(mu[0, 0].item(), 15.0)  # (10 + 20)/2
    assert np.isclose(mu[0, 1].item(), 10.0)  # (5 + 15)/2
    assert np.isclose(mu[1, 0].item(), 30.0)  # 30/1
    assert sd[0, 0].item() > 0.0


def test_journeynorm_denormalization_channel_schema():
    """Verify that de-normalization strictly maps to SeqSchema.ARR_DELAY channel (Bug 5)."""
    from ml.model_v2 import SeqSchema
    model = RailTwinGRUv2(hidden_dim=32, gru_layers=1)
    
    # Mock head to output constant 1.0
    class MockHead(torch.nn.Module):
        def forward(self, h):
            return torch.ones((h.size(0), len(ALPHAS_V2)), dtype=torch.float32)
    
    model.head = MockHead()
    
    # Construct sequence where arr_delay has mean=20.0, sd=5.0
    # and dep_delay has mean=50.0, sd=10.0
    seq = torch.zeros((1, 4, 8), dtype=torch.float32)
    seq[0, 0, SeqSchema.ARR_DELAY] = 15.0
    seq[0, 1, SeqSchema.ARR_DELAY] = 25.0
    seq[0, 0, SeqSchema.DEP_DELAY] = 40.0
    seq[0, 1, SeqSchema.DEP_DELAY] = 60.0
    
    mask = torch.tensor([[True, True, False, False]])
    stn_ids = torch.zeros((1, 4), dtype=torch.long)
    ctx = torch.zeros((1, 34), dtype=torch.float32)
    
    out = model(seq, stn_ids, mask, ctx)
    q = out["quantiles"]
    
    # Expected: mu_arr + 1.0 * sd_arr = 20.0 + 5.0 = 25.0
    # NOT dep_delay stats (50 + 10 = 60)
    mu_arr, sd_arr = JourneyNorm.masked_stats(seq[..., [SeqSchema.ARR_DELAY]], mask)
    expected_q = (mu_arr + sd_arr).item()
    assert np.isclose(q[0, 0].item(), expected_q, atol=1e-3)

