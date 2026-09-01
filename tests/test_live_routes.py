"""Unit and Integration tests for Pipeline 07 Live Routes & SSE (Phase A6, A8)."""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import settings
from data.db import Database, get_db
from engine.clocks import RealClock, ReplayClock, set_global_clock


@pytest.fixture
def client():
    return TestClient(app)


def test_meta_config_endpoint(client):
    """Verifies GET /v1/meta/config returns all runtime configuration constants."""
    response = client.get("/v1/meta/config")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "intervals" in data
    assert "thresholds" in data
    assert "budgets" in data
    assert "delay_colors" in data
    assert "attribution_colors" in data
    assert data["intervals"]["live_tracker_interval_seconds"] == settings.LIVE_TRACKER_INTERVAL_SECONDS
    assert data["thresholds"]["attribution_delta_min"] == settings.ATTRIBUTION_DELTA_MIN
    assert "RAKE_INHERIT" in data["attribution_colors"]
    assert "UNEXPLAINED" in data["attribution_colors"]


def test_get_live_positions(client):
    """Verifies GET /v1/live/positions returns active train positions array."""
    response = client.get("/v1/live/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "positions" in data
    assert isinstance(data["positions"], list)


def test_get_train_live_known_and_unknown(client):
    """Verifies GET /v1/trains/{train_no}/live returns position, context, and why-late for valid train, and 404 for unknown."""
    # Unknown train
    resp_404 = client.get("/v1/trains/999999/live")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()

    # Known train
    resp_200 = client.get("/v1/trains/12301/live")
    assert resp_200.status_code == 200
    data = resp_200.json()
    assert data["train_no"] == "12301"
    assert "position" in data
    assert "context" in data
    assert "why_late" in data
    assert 25.0 <= data["position"]["lat"] <= 29.0
    assert 77.0 <= data["position"]["lng"] <= 83.5


def test_get_train_why_late(client):
    """Verifies GET /v1/trains/{train_no}/why-late returns causal attribution summary."""
    resp = client.get("/v1/trains/12301/why-late")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "12301"
    assert "cause_breakdown" in data
    assert "is_exact_accounting" in data
    assert data["is_exact_accounting"] is True


def test_live_stream_sse_endpoint(client):
    """Verifies GET /v1/live/stream returns text/event-stream content type and pulses."""
    with client.stream("GET", "/v1/live/stream?max_frames=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        # Read the initial event frame
        for line in response.iter_lines():
            if line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                assert "event" in payload
                assert payload["event"] in ("initial_state", "pulse", "position_update")
                assert "positions" in payload
                break
