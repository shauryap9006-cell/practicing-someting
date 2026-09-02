"""Unit tests for Mid-Section Signal-Hold Inference (Proposal 3)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db
from engine.live_tracker import LivePositionTracker, LiveTrainPosition


@pytest.fixture
def client():
    return TestClient(app)


def test_live_position_tracker_computes_signal_aspect():
    """LivePositionTracker must compute inferred signal aspects and signal hold duration."""
    db = get_db()
    tracker = LivePositionTracker(db)
    
    # Query a live position for a known train
    with db.transaction() as cur:
        cur.execute("SELECT train_no FROM trains LIMIT 1;")
        row = cur.fetchone()
        sample_train = row["train_no"] if row else "12004"
        
    pos = tracker.get_live_position(sample_train)
    if pos:
        assert "inferred_signal_aspect" in pos
        assert pos["inferred_signal_aspect"] in ("GREEN", "DOUBLE_YELLOW", "YELLOW", "RED")
        assert "signal_hold_active" in pos
        assert isinstance(pos["signal_hold_active"], bool)
        assert "signal_hold_duration_min" in pos
        assert pos["signal_hold_duration_min"] >= 0.0


def test_signal_hold_inference_in_live_api(client):
    """GET /v1/live/positions must expose signal aspects and signal hold status for UI telemetry."""
    response = client.get("/v1/live/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "positions" in data
    
    if data["positions"]:
        first = data["positions"][0]
        assert "inferred_signal_aspect" in first
        assert "signal_hold_active" in first
        assert "signal_hold_duration_min" in first
