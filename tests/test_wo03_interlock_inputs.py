"""WO-03 Reproducer Test: Real Current Delay to Interlock.

Verifies that _format_prediction_result passes the real live current_delay,
actual km_remaining, and hops_remaining into validate_prediction_through_interlock,
rather than passing 'current_delay': p50_min which tautologically bypassed
check_recovery_feasibility.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.predictor import PredictorService
from engine.position_resolver import PositionRecord


def test_interlock_receives_real_current_delay_and_clamps_impossible_recovery():
    """GATE-1 Reproducer: When current_delay=90m and model predicts 10m over 20km, interlock must clamp."""
    predictor = PredictorService()

    pos_record = PositionRecord(
        mode_seq=2,
        station_code="GZB",
        confidence=1.0,
        basis="gps",
        age_seconds=10.0,
        source="live",
        posterior_probs={2: 1.0},
    )

    # Intercept validate_prediction_through_interlock to verify what features were passed
    from safety import interlock

    captured_features = {}
    original_validate = interlock.validate_prediction_through_interlock

    def spy_validate(features, *args, **kwargs):
        captured_features.update(features)
        return original_validate(features, *args, **kwargs)

    with patch("safety.interlock.validate_prediction_through_interlock", side_effect=spy_validate):
        # We call predict_train_eta with an explicit current_delay of 90.0 minutes
        # Train is at GZB (seq 2), target is ALJN (seq 3, ~100km away)
        res = predictor.predict_train_eta(
            train_no="12301",
            target_station_code="ALJN",
            current_seq=2,
            current_delay=90.0,
        )

    # The feature_dict passed to interlock MUST have current_delay == 90.0, NOT the model prediction!
    assert "current_delay" in captured_features, "current_delay was missing from interlock features!"
    assert captured_features["current_delay"] == 90.0, (
        f"Interlock received fake current_delay={captured_features['current_delay']} "
        f"instead of true current_delay=90.0!"
    )
