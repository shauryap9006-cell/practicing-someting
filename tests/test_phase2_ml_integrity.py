"""Test Suite for Phase 2: ML Integrity & Dispatch Restructure (D01, D02, D07, D08, D09, D13)."""
from __future__ import annotations

import pytest
import numpy as np
from api.predictor import get_predictor_service, enforce_quantile_order
from config import settings


def test_enforce_quantile_order_monotonicity():
    """Asserts D09: enforce_quantile_order guarantees p10 <= p50 <= p90 under all crossing/NaN inputs."""
    # Crossing inputs: p10 > p50 > p90
    p10, p50, p90 = enforce_quantile_order(50.0, 30.0, 10.0)
    assert p10 <= p50 <= p90
    assert p10 >= 0.0

    # Crossing inputs with cap
    p10_c, p50_c, p90_c = enforce_quantile_order(100.0, 80.0, 120.0, cap=90.0)
    assert p10_c <= p50_c <= p90_c
    assert p90_c <= 90.0

    # Negative inputs clamped to >= 0
    p10_n, p50_n, p90_n = enforce_quantile_order(-10.0, -5.0, 15.0)
    assert p10_n >= 0.0
    assert p10_n <= p50_n <= p90_n

    # NaN / Inf inputs handled safely
    p10_nan, p50_nan, p90_nan = enforce_quantile_order(float("nan"), 20.0, float("inf"))
    assert p10_nan <= p50_nan <= p90_nan
    assert not np.isnan(p10_nan)
    assert not np.isinf(p90_nan)


def test_ensemble_dispatch_primary_serving(monkeypatch):
    """Asserts D01: Primary served prediction uses 5-Model Ensemble when tsr_active_ahead_count == 0."""
    predictor = get_predictor_service()
    assert hasattr(predictor, "_ensemble")
    assert predictor._ensemble is not None

    # Monkeypatch ensemble predict to return distinct fixed values
    expected_output = (11.0, 22.0, 33.0)
    monkeypatch.setattr(predictor._ensemble, "predict", lambda *args, **kwargs: expected_output)

    orig_extract = predictor.snapshot_gen.extract_features_at_snapshot
    def mock_extract(*args, **kwargs):
        vec = orig_extract(*args, **kwargs)
        vec.tsr_active_ahead_count = 0
        return vec
    monkeypatch.setattr(predictor.snapshot_gen, "extract_features_at_snapshot", mock_extract)

    res = predictor.predict_train_eta("12004", "CNB")
    assert res["tier_used"] == "Tier2_Convex_Ensemble_NNLS"
    assert res["pred_delay_p50"] == pytest.approx(22.0)
    assert res["pred_delay_p10"] == pytest.approx(11.0)
    assert res["pred_delay_p90"] == pytest.approx(33.0)
    assert res["model"]["name"] == "Tier2_Convex_Ensemble_NNLS"


def test_ensemble_dispatch_with_tsr_penalty(monkeypatch):
    """Asserts D01: TSR penalty is an additive post-adjustment to ensemble prediction."""
    predictor = get_predictor_service()
    expected_output = (11.0, 22.0, 33.0)
    monkeypatch.setattr(predictor._ensemble, "predict", lambda *args, **kwargs: expected_output)

    orig_extract = predictor.snapshot_gen.extract_features_at_snapshot
    def mock_extract(*args, **kwargs):
        vec = orig_extract(*args, **kwargs)
        vec.tsr_active_ahead_count = 2  # 2 active TSRs -> max(8.0, 16.0) = 16.0 penalty
        return vec
    monkeypatch.setattr(predictor.snapshot_gen, "extract_features_at_snapshot", mock_extract)

    res = predictor.predict_train_eta("12004", "CNB")
    assert res["tier_used"] == "Tier2_Convex_Ensemble_NNLS"
    assert res["pred_delay_p50"] == pytest.approx(22.0 + 16.0)
    assert res["pred_delay_p10"] == pytest.approx(11.0 + 16.0)
    assert res["pred_delay_p90"] == pytest.approx(33.0 + 16.0)


def test_gru_challenger_retired_from_served_champion():
    """Asserts D02: GRU challenger is gated and not served as champion."""
    predictor = get_predictor_service()
    assert predictor._gru_sequence_ready is False
    model_info = predictor.get_model_info()
    assert model_info["served_model"] != "PyTorch_GRU_Quantile"
    assert model_info["tiers_available"]["neural_gru"] is False
