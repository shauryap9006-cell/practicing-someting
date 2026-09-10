"""WO-04 Reproducer Test: Terminus and Arrived Station Semantics.

When all candidates are >= target_seq (or train is at/past terminus),
predictor previously fell back to seq_k = 1 and predicted an entire journey
from the beginning of the corridor. It must return ARRIVED status with actual arrival semantics.
"""

import pytest

from api.predictor import PredictorService
from data.db import get_db


@pytest.fixture
def db():
    database = get_db()
    database.init_schema()
    return database


def test_train_already_at_target_station_returns_arrived_semantics(db):
    """GATE-1 Reproducer: Querying ETA for station train has already reached returns ARRIVED status."""
    predictor = PredictorService(db)

    # Train 12301: NDLS (1) -> CNB (4) -> PRYJ (5) -> DDU (7) -> HWH (10)
    # If train is currently at CNB (seq=4) and target is CNB (seq=4) or NDLS (seq=1)
    res = predictor.predict_train_eta(
        train_no="12301",
        target_station_code="CNB",
        current_seq=6,
        current_delay=15.0,
    )

    # In current code:
    # Because current_seq (4) >= target_seq (4), preds is empty,
    # and it falls back to seq_k = 1, predicting travel from NDLS (seq 1) to CNB (seq 4)!
    # The fix must detect arrival: status == "ARRIVED" and is_arrived is True.
    assert res.get("status") == "ARRIVED" or res.get("is_arrived") is True, (
        f"Train already at CNB was predicted from corridor start (seq=1)! Result: {res}"
    )
    # Delay must match current terminal delay (15m), not a regenerated forecast
    assert res["predicted_delay_min"] == 15
    # For arrived train, uncertainty band width should be 0.0
    assert res["band_width_min"] == 0.0 or res["confidence_band"]["band_width_min"] == 0.0


def test_train_already_passed_station_returns_arrived_semantics(db):
    """Verifies that querying a historical/passed station returns ARRIVED rather than predicting from origin."""
    predictor = PredictorService(db)

    # Train is at ON (seq=7), target was TDL (seq=4)
    res = predictor.predict_train_eta(
        train_no="12301",
        target_station_code="TDL",
        current_seq=7,
        current_delay=20.0,
    )

    assert res["status"] == "ARRIVED"
    assert res["is_arrived"] is True
    assert res["band_width_min"] == 0.0
