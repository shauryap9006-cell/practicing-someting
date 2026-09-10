"""WO-05 Reproducer Test: Real Feature Attribution in Predictor.

Verifies that predict_train_eta passes the real feature vector/DataFrame
from snapshot extraction to _extract_top_drivers, rather than passing df_feat=None
which falls back to hardcoded constant 75/15/10 breakdown.
"""

from unittest.mock import MagicMock, patch
import pytest

from api.predictor import PredictorService
from ml.features import TrainFeatureVector


def make_test_vector(**kwargs):
    defaults = {
        "current_delay": 0.0,
        "hops_remaining": 1,
        "km_remaining": 50.0,
        "hour_of_day": 10,
        "day_type": 0,
        "train_priority": 1,
        "target_is_junction": 0,
        "target_is_terminus": 0,
        "hist_avg_delay_train_target": 0.0,
        "hist_p90_delay_train_target": 5.0,
        "sched_halt_target_min": 2,
        "sched_congestion_target": 0,
        "fog_flag_target": 0,
        "rain_mm_target": 0.0,
        "active_corridor_trains": 1,
        "delay_velocity": 0.0,
        "chronic_baseline": 0.0,
    }
    defaults.update(kwargs)
    return TrainFeatureVector(**defaults)


def test_real_feature_attribution_fog_driver():
    """GATE-1 Reproducer: When fog_flag_target=1, top driver must be severe_fog_visibility."""
    predictor = PredictorService()

    real_vec = make_test_vector(fog_flag_target=1)

    with patch.object(predictor.snapshot_gen, "extract_features_at_snapshot", return_value=real_vec):
        res = predictor.predict_train_eta(
            train_no="12301",
            target_station_code="ALJN",
            current_seq=2,
            current_delay=0.0,
        )

    drivers = res.get("drivers", [])
    assert len(drivers) > 0, "No drivers returned in prediction result!"
    top_driver = drivers[0]

    # In buggy code: df_feat=None is passed, so drivers are the hardcoded 75/15/10 breakdown:
    # [{'feature': 'incurred_upstream_delay', ...}, {'feature': 'corridor_section_headway', ...}, ...]
    # In fixed code: real features are passed, so fog is detected as top driver:
    assert top_driver["feature"] == "severe_fog_visibility", (
        f"Expected top driver 'severe_fog_visibility', but got '{top_driver['feature']}'. "
        f"All drivers: {drivers}"
    )


def test_real_feature_attribution_congestion_driver():
    """GATE-1 Reproducer: When downstream congestion is high, downstream_section_congestion must be reported."""
    predictor = PredictorService()

    real_vec = make_test_vector(
        trains_ahead_30k=4.0,
        sum_delay_trains_ahead_30k=50.0,
    )

    with patch.object(predictor.snapshot_gen, "extract_features_at_snapshot", return_value=real_vec):
        res = predictor.predict_train_eta(
            train_no="12301",
            target_station_code="ALJN",
            current_seq=2,
            current_delay=0.0,
        )

    driver_names = [d["feature"] for d in res.get("drivers", [])]
    assert "downstream_section_congestion" in driver_names, (
        f"Expected 'downstream_section_congestion' in drivers, but got {driver_names}"
    )
