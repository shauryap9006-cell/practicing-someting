"""Integration & Contract Tests for FastAPI REST API (M5 - F11).

Tests all 10 /v1/ endpoints using FastAPI TestClient to ensure standard response
contracts, accurate status codes, and non-empty payloads.
"""

from fastapi.testclient import TestClient
import pytest

from api.main import app

client = TestClient(app)


def test_api_health():
    """Verifies /v1/health endpoint."""
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "connected" in data["db"]
    assert data["clock_mode"] in ["live", "replay"]


def test_api_train_eta():
    """Verifies /v1/trains/{train_no}/eta endpoint."""
    resp = client.get("/v1/trains/12034/eta?station=NDLS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "12034"
    assert data["target_station"] == "NDLS"
    assert "confidence_band" in data
    assert "predicted_arr" in data
    assert data["clock_mode"] in ["live", "replay"]


def test_api_train_journey():
    """Verifies /v1/trains/{train_no}/journey timeline endpoint."""
    resp = client.get("/v1/trains/12034/journey")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "12034"
    assert len(data["timeline"]) >= 7
    assert data["timeline"][0]["status_color"] in ["green", "amber", "red"]


def test_api_train_autopsy():
    """Verifies /v1/trains/{train_no}/autopsy endpoint."""
    resp = client.get("/v1/trains/12034/autopsy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "12034"
    # is_exact_accounting is True when sim_ledger events exist, False for historical fallback
    assert isinstance(data["is_exact_accounting"], bool)
    assert len(data["causes"]) > 0


def test_api_network_state():
    """Verifies /v1/network/state corridor overview endpoint."""
    resp = client.get("/v1/network/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_trains_count"] > 0
    assert len(data["trains"]) > 0
    assert len(data["active_tsrs"]) >= 1


def test_api_station_gantt():
    """Verifies /v1/stations/{code}/gantt platform endpoint."""
    resp = client.get("/v1/stations/NDLS/gantt")
    assert resp.status_code == 200
    data = resp.json()
    assert data["station_code"] == "NDLS"
    assert data["total_platforms"] >= 8
    assert len(data["blocks"]) > 0


def test_api_station_reoptimize():
    """Verifies POST /v1/stations/{code}/reoptimize 1-click self-heal endpoint."""
    resp = client.post("/v1/stations/NDLS/reoptimize", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["station_code"] == "NDLS"
    assert data["execution_time_seconds"] < 2.0
    assert "conflicts_before" in data
    assert "conflicts_after" in data


def test_api_what_if_simulation():
    """Verifies POST /v1/simulate/what-if cascade simulation endpoint."""
    payload = {
        "train_no": "12034",
        "station_code": "CNB",
        "injected_delay_min": 90,
    }
    resp = client.post("/v1/simulate/what-if", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario"]["train_no"] == "12034"
    assert data["affected_trains_count"] > 0


def test_api_crew_alerts():
    """Verifies /v1/crew/alerts duty breach endpoint."""
    resp = client.get("/v1/crew/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_alerts" in data
    assert "alerts" in data


def test_api_meta_models():
    """Verifies /v1/meta/models metadata & proof table endpoint."""
    resp = client.get("/v1/meta/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "manifest" in data


# ----------------------------------------------------
# Phase 5: Dispatcher ACK contract tests
# ----------------------------------------------------
def test_api_dispatcher_ack_accepted():
    """Verifies POST /v1/advise/{adv_id}/ack records 'accepted' decision."""
    resp = client.post(
        "/v1/advise/test-adv-001/ack",
        json={"decision": "accepted", "dispatcher_id": "DISP-42", "comment": "Approved"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adv_id"] == "test-adv-001"
    assert data["decision"] == "accepted"
    assert data["status"] == "ok"
    assert "recorded_at" in data


def test_api_dispatcher_ack_rejected():
    """Verifies POST /v1/advise/{adv_id}/ack records 'rejected' decision."""
    resp = client.post(
        "/v1/advise/test-adv-002/ack",
        json={"decision": "rejected", "comment": "Too conservative — train can proceed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adv_id"] == "test-adv-002"
    assert data["decision"] == "rejected"
    assert data["status"] == "ok"


def test_api_dispatcher_ack_invalid():
    """Verifies POST /v1/advise/{adv_id}/ack rejects invalid decision values."""
    resp = client.post(
        "/v1/advise/test-adv-003/ack",
        json={"decision": "maybe"},
    )
    assert resp.status_code == 400

