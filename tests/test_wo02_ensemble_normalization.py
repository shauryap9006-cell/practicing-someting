"""WO-02 Reproducer Test: Ensemble Weight Normalization Defect.

When seq_tensor is None (or GRU is unavailable), the fallback formula dropped w_gru
without re-normalizing the remaining active weights (sum = 0.80 - 0.95), deflating
all predicted delays by 5% to 20%.
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from ml.ensemble import EnsemblePredictor


def test_fallback_ensemble_weights_sum_to_one_when_gru_absent():
    """GATE-1 Reproducer: Ensure constant input yields identical constant output without deflation."""
    ensemble = EnsemblePredictor()

    # Mock candidate models to all predict 30.0 minutes delay
    mock_booster = MagicMock()
    mock_booster.predict = MagicMock(return_value=np.array([30.0]))
    ensemble._gbm_models = {0.1: mock_booster, 0.5: mock_booster, 0.9: mock_booster}

    mock_lr = MagicMock()
    mock_lr.predict = MagicMock(return_value=np.array([30.0]))
    ensemble._lr_model = mock_lr

    # Feature array: feature 0 (current_delay) = 30.0, hops = 5, km = 150.0 (medium horizon: sum without GRU is 0.80)
    feat_np = np.zeros((1, 10))
    feat_np[0, 0] = 30.0  # current_delay = 30.0 (b1)
    feat_np[0, 1] = 5     # hops
    feat_np[0, 2] = 150.0 # km_remaining

    # Call predict with seq_tensor = None
    # Disable CQR adjustment for pure raw weight test or inspect raw behavior
    # Note: If all submodels predict 30.0, raw_p50 before CQR must be 30.0, NOT 24.0 (0.80 * 30)!
    # With raw_p50 deflated to 24.0, final p50 is dragged down by 6.0 minutes.

    # We can mock mondrian_cqr.adjust_interval to be identity on p50
    ensemble.mondrian_cqr.adjust_interval = MagicMock(
        side_effect=lambda p10, p90, raw_p50, **kwargs: (p10, p90, 0.0)
    )

    p10, p50, p90 = ensemble.predict(
        feature_df=feat_np,
        seq_tensor=None,
        hops=5,
        km_remaining=150.0,
    )

    # In medium bucket: w_gbm=0.40, w_gru=0.20, w_lr=0.10, w_b1=0.20, w_b3=0.10
    # Active weights sum = 0.80.
    # Without normalization: p50 = 0.4*30 + 0.1*30 + 0.2*30 + 0.1*30 = 24.0.
    # With normalization: active weights sum to 1.0, so p50 == 30.0!
    assert abs(p50 - 30.0) < 1e-3, (
        f"Ensemble weights were not re-normalized when GRU is absent! "
        f"Expected p50=30.0, but got p50={p50} (deflation of {30.0 - p50:.2f}m / {(30.0 - p50)/30.0*100:.1f}%)"
    )
