"""WO-09 Verification Gate: Serve PyTorch GRU Challenger in Ensemble.

GATES:
T1: Stacking weight-sum == 1.0 across all horizons with GRU active (w_gru > 0).
T2: Perturb the GRU output -> ensemble output changes (GRU demonstrably contributes).
T3: In serving path (predict_train_eta), seq_tensor is dynamically constructed
    from telemetry history, passed to ensemble, and p95 inference latency stays < 100ms.
"""

import time
import pytest
import torch
import numpy as np

from api.predictor import get_predictor_service
from ml.ensemble import EnsemblePredictor


def test_wo09_stacking_weights_sum_to_one_with_gru_active():
    """GATE-T1: Weight sum == 1.0 with GRU active across short, medium, long horizons."""
    ens = EnsemblePredictor()
    assert ens._gru_model is not None, "GRU model must be loaded in EnsemblePredictor"

    for horizon in ["short", "medium", "long"]:
        weights = ens.stacking_weights[horizon]
        assert len(weights) == 5, f"Expected 5-model weights in {horizon}"
        w_gbm, w_gru, w_lr, w_b1, w_b3 = weights
        assert w_gru > 0.0, f"GRU weight must be > 0 in {horizon}, got {w_gru}"
        w_sum = sum(weights)
        assert pytest.approx(w_sum, rel=1e-5) == 1.0, f"Weight sum must be 1.0 in {horizon}, got {w_sum}"


def test_wo09_gru_perturbation_changes_ensemble_output():
    """GATE-T2: Perturb the GRU output -> ensemble output changes (GRU demonstrably contributes)."""
    ens = EnsemblePredictor()
    arr_feat = np.zeros((1, 25), dtype=np.float32)
    seq_tensor = torch.zeros((1, 8, 8), dtype=torch.float32)

    class MockGRU(torch.nn.Module):
        def __init__(self, val):
            super().__init__()
            self.val = val

        def forward(self, inp):
            v = torch.tensor([[self.val]], dtype=torch.float32)
            return v - 2.0, v, v + 5.0

    orig_gru = ens._gru_model
    try:
        # Prediction with GRU output = 10.0
        ens._gru_model = MockGRU(10.0)
        p10_1, p50_1, p90_1 = ens.predict(arr_feat, seq_tensor=seq_tensor, hops=3, km_remaining=150)

        # Prediction with GRU output = 50.0
        ens._gru_model = MockGRU(50.0)
        p10_2, p50_2, p90_2 = ens.predict(arr_feat, seq_tensor=seq_tensor, hops=3, km_remaining=150)

        # GRU must demonstrably shift ensemble output
        diff = p50_2 - p50_1
        assert diff > 1.0, f"Perturbing GRU (+40m) must shift ensemble output, got diff={diff:.3f}"
    finally:
        ens._gru_model = orig_gru


def test_wo09_serving_path_constructs_seq_tensor_and_measures_latency():
    """GATE-T3: predict_train_eta builds seq_tensor, serves GRU, and latency < 100ms."""
    predictor = get_predictor_service()

    # Verify helper exists and builds valid tensor
    assert hasattr(predictor, "build_sequence_tensor"), "PredictorService must implement build_sequence_tensor"

    # Route fixture for train 12034
    predictor.snapshot_gen._load_metadata_caches()
    routes_dict = predictor.snapshot_gen._cached_routes or {}
    route = routes_dict.get("12034", [])
    assert len(route) >= 2

    # If train has observed stops (seq >= 1), sequence tensor must be generated
    events_mock = {1: 10.0, 2: 12.0}
    seq_tensor = predictor.build_sequence_tensor(
        route=route,
        current_seq=2,
        events_by_seq=events_mock,
        current_delay=12.0,
    )
    assert seq_tensor is not None, "seq_tensor must not be None when train has sequence history"
    assert seq_tensor.shape == (1, 8, 8), f"Expected shape (1, 8, 8), got {seq_tensor.shape}"

    # Verify sequence availability dynamic check (never hardcoded True)
    assert predictor.build_sequence_tensor([], 0, {}, 0.0) is None

    # Warmup
    res = predictor.predict_train_eta("12034", "ALJN")
    assert res["tier_used"] == "Tier2_Convex_Ensemble_NNLS"

    # Verify end-to-end serving path latency < 100ms
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        res = predictor.predict_train_eta("12034", "ALJN")
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p95_latency = np.percentile(latencies, 95)
    assert p95_latency < 100.0, f"Serving p95 latency {p95_latency:.2f}ms exceeds 100ms"
