"""RailTwin-X Neural Architecture Tests (F07, F08, F09, F16).

Verifies:
1. Masked Attention (F08): Padding positions receive exactly 0.0 attention mass.
2. FiLM Context Conditioning (F07): Modulates outputs conditionally on tabular context.
3. Station Embeddings (F09): 1200-dim station embedding and hash fallback for unseen stations.
4. Non-Crossing Heads (F16): Guaranteed monotonic ordering 0 <= q10 <= q50 <= q90.
5. End-to-end gradient flow through all neural components.
"""

import numpy as np
import pytest
import torch
from ml.model_seq import (
    NonCrossingGRUQuantileModel,
    FiLMLayer,
    station_code_to_idx,
    PinballQuantileLoss,
)


def test_station_code_hashing():
    """Asserts deterministic station code indexing and fallback for novel stations (F09)."""
    idx_ndls = station_code_to_idx("NDLS")
    idx_cnb = station_code_to_idx("CNB")
    idx_ddu = station_code_to_idx("DDU")
    idx_unknown = station_code_to_idx("XYZ999")

    assert 0 <= idx_ndls < 1200
    assert 0 <= idx_cnb < 1200
    assert 0 <= idx_ddu < 1200
    assert 0 <= idx_unknown < 1200
    assert idx_ndls != idx_cnb  # Distinct codes map distinctly


def test_masked_temporal_attention_zero_mass():
    """Asserts that padding positions receive strictly 0.0 attention weight (F08)."""
    torch.manual_seed(42)
    model = NonCrossingGRUQuantileModel(input_dim=8, hidden_dim=64, num_layers=1)
    model.eval()

    # Batch of 2 samples, seq_len=6.
    # Sample 0: first 4 steps are padding, last 2 steps are valid
    # Sample 1: first 2 steps are padding, last 4 steps are valid
    x = torch.randn(2, 6, 8)
    mask = torch.tensor([
        [False, False, False, False, True, True],
        [False, False, True, True, True, True],
    ], dtype=torch.bool)

    with torch.no_grad():
        q10, q50, q90 = model(x, mask=mask)

    attn_weights = model.last_attn_weights.squeeze(-1)  # [2, 6]

    # Check that masked positions have 0.0 attention mass
    assert torch.all(attn_weights[0, :4] < 1e-6), f"Sample 0 padded positions have nonzero attention: {attn_weights[0, :4]}"
    assert torch.all(attn_weights[1, :2] < 1e-6), f"Sample 1 padded positions have nonzero attention: {attn_weights[1, :2]}"

    # Check that sum of attention weights across time equals 1.0
    attn_sums = attn_weights.sum(dim=1)
    assert torch.allclose(attn_sums, torch.ones(2), atol=1e-5)


def test_film_context_modulation():
    """Asserts that varying context vector changes model predictions significantly (F07)."""
    torch.manual_seed(42)
    model = NonCrossingGRUQuantileModel(input_dim=8, context_dim=25, hidden_dim=64)
    model.eval()

    x = torch.randn(1, 8, 8)

    # Clear weather context vs severe fog/congestion context
    ctx_clear = torch.zeros(1, 25)
    ctx_fog = torch.zeros(1, 25)
    ctx_fog[0, 0] = 1.0  # fog_flag
    ctx_fog[0, 1] = 5.0  # heavy congestion

    with torch.no_grad():
        q10_clear, q50_clear, q90_clear = model(x, context=ctx_clear)
        q10_fog, q50_fog, q90_fog = model(x, context=ctx_fog)

    # Modulated outputs should differ
    assert not torch.allclose(q50_clear, q50_fog, atol=1e-4), "Context should modulate predictions via FiLM"


def test_non_crossing_monotonicity():
    """Asserts that 0 <= q10 <= q50 <= q90 holds across 100 random batch inputs (F16)."""
    torch.manual_seed(42)
    model = NonCrossingGRUQuantileModel(input_dim=8, hidden_dim=64, num_layers=2)
    model.eval()

    x = torch.randn(100, 8, 8) * 10.0
    ctx = torch.randn(100, 25)
    stn_idx = torch.randint(0, 1200, (100,))

    with torch.no_grad():
        q10, q50, q90 = model(x, context=ctx, target_station_idx=stn_idx)

    assert torch.all(q10 >= 0.0), "q10 should be non-negative (delay >= 0)"
    assert torch.all(q10 <= q50), "q10 must be <= q50"
    assert torch.all(q50 <= q90), "q50 must be <= q90"


def test_end_to_end_gradient_flow():
    """Asserts that pinball loss propagates gradients through all sub-modules."""
    torch.manual_seed(42)
    model = NonCrossingGRUQuantileModel(input_dim=8, context_dim=25, hidden_dim=64, num_layers=2)
    model.train()

    x = torch.randn(4, 8, 8, requires_grad=True)
    ctx = torch.randn(4, 25, requires_grad=True)
    stn_idx = torch.tensor([12, 45, 108, 502], dtype=torch.long)
    target = torch.tensor([12.0, 35.0, 5.0, 60.0])

    criterion = PinballQuantileLoss()
    q10, q50, q90 = model(x, context=ctx, target_station_idx=stn_idx)
    loss = criterion(q10, q50, q90, target)

    loss.backward()

    # Verify gradients on GRU, attention, FiLM, and station embedding
    assert model.gru.weight_ih_l0.grad is not None
    assert model.attn.weight.grad is not None
    assert model.film.fc_gamma.weight.grad is not None
    assert model.station_embed.weight.grad is not None
    assert model.head_q10.weight.grad is not None
