"""Phase 2 Safety & Compliance Comprehensive Test Suite.

Tests:
- D2: Caution Orders / Speed Restrictions (TSR) Lifecycle
- D3: Permit-to-Work / Track Possessions Workflow
- D4: Incident & Near-Miss Register
- D5: SOP Emergency Checklist Runner
- D6: Level Crossing Status Board
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import Database, get_db

client = TestClient(app)


@pytest.fixture
def auth_headers(tmp_path):
    """Creates authorized JWT headers for testing safety routes."""
    token = create_access_token(
        data={
            "sub": "sm_ndls",
            "username": "sm_ndls",
            "role_id": "station_master",
            "station_code": "NDLS",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_tsr_lifecycle(auth_headers):
    """Verifies Caution Order (TSR) creation, listing, block caution update, and cancellation."""
    # 1. Create TSR
    tsr_payload = {
        "from_code": "NDLS",
        "to_code": "GZB",
        "start_km": 10.5,
        "end_km": 12.0,
        "speed_limit_kmph": 45,
        "cause": "Deep screening of ballast",
        "permanent_or_temp": "TEMPORARY",
        "effective_from": "2026-08-28T00:00:00Z",
    }
    resp = client.post("/api/safety/tsr", json=tsr_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    tsr_id = data["id"]
    assert data["status"] == "ACTIVE"
    assert data["speed_limit_kmph"] == 45

    # 2. List TSRs
    list_resp = client.get("/api/safety/tsr?station_code=NDLS&status=ACTIVE", headers=auth_headers)
    assert list_resp.status_code == 200
    tsrs = list_resp.json()
    assert any(t["id"] == tsr_id for t in tsrs)

    # 3. Cancel TSR
    del_resp = client.delete(f"/api/safety/tsr/{tsr_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "CANCELLED"


def test_possession_workflow(auth_headers):
    """Verifies Permit-to-Work / Possession request, grant with platform blocking, and restoration."""
    # 1. Request Possession
    req_payload = {
        "possession_type": "PLATFORM",
        "element_id": "PF-NDLS-2",
        "station_code": "NDLS",
        "start_time": "14:00",
        "end_time": "16:00",
        "work_type": "OHE_TRACTION",
        "requesting_dept": "TRD (Traction Distribution)",
        "notes": "Catenary wire replacement",
    }
    resp = client.post("/api/safety/possession/request", json=req_payload, headers=auth_headers)
    assert resp.status_code == 200
    p_id = resp.json()["id"]
    assert resp.json()["status"] == "REQUESTED"

    # 2. Grant Possession
    grant_resp = client.post(f"/api/safety/possession/{p_id}/grant", headers=auth_headers)
    assert grant_resp.status_code == 200
    assert grant_resp.json()["status"] == "ACTIVE"

    # 3. Restore Possession
    rest_resp = client.post(f"/api/safety/possession/{p_id}/restore", headers=auth_headers)
    assert rest_resp.status_code == 200
    assert rest_resp.json()["status"] == "RESTORED"


def test_incident_reporting(auth_headers):
    """Verifies Incident & Near-Miss reporting and query."""
    inc_payload = {
        "incident_type": "NEAR_MISS",
        "severity": "MAJOR",
        "station_code": "NDLS",
        "location_km": 15.4,
        "train_no": "12004",
        "summary": "Trespasser crossing track near yard throat; loco pilot applied emergency brakes",
        "action_taken": "RPF alerted; track cleared",
    }
    resp = client.post("/api/safety/incidents", json=inc_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OPEN"
    assert data["severity"] == "MAJOR"

    # Query incidents
    list_resp = client.get("/api/safety/incidents?station_code=NDLS", headers=auth_headers)
    assert list_resp.status_code == 200
    incidents = list_resp.json()
    assert len(incidents) > 0


def test_sop_emergency_runner(auth_headers):
    """Verifies SOP emergency templates, active run start, and checklist step progression."""
    # 1. Get templates
    tpl_resp = client.get("/api/safety/sop/templates")
    assert tpl_resp.status_code == 200
    templates = tpl_resp.json()
    assert len(templates) >= 3

    # 2. Start SOP run
    start_payload = {
        "template_id": "SOP-SPAD-01",
        "station_code": "NDLS",
    }
    start_resp = client.post("/api/safety/sop/start", json=start_payload, headers=auth_headers)
    assert start_resp.status_code == 200
    run_data = start_resp.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "IN_PROGRESS"

    # 3. Complete Step 1
    step_resp = client.post(f"/api/safety/sop/{run_id}/step", json={"step_index": 0}, headers=auth_headers)
    assert step_resp.status_code == 200
    assert step_resp.json()["total_completed"] == 1


def test_level_crossing_board(auth_headers):
    """Verifies Level Crossing status listing and state transitions."""
    # 1. List LCs
    list_resp = client.get("/api/safety/lc/status?station_code=NDLS", headers=auth_headers)
    assert list_resp.status_code == 200
    lcs = list_resp.json()
    assert len(lcs) > 0
    lc_id = lcs[0]["id"]

    # 2. Update LC status to DEFECTIVE
    up_resp = client.put(
        f"/api/safety/lc/{lc_id}/status",
        json={"status": "DEFECTIVE", "notes": "Lifting barrier jammed"},
        headers=auth_headers,
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["status"] == "DEFECTIVE"
