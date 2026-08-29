"""Phase 4 Workforce & Crew Intelligence Test Suite.

Tests:
- F1: Digital Breathalyzer Register & Zero-Tolerance Interlock
- F2: Crew CMS Sign-On/Sign-Off & Duty Breach Engine
- F3: Staff Shift Scheduler
- F4: Sahayak Porter Roster
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Creates authorized JWT headers for testing workforce routes."""
    token = create_access_token(
        data={
            "sub": "sm_ndls",
            "username": "sm_ndls",
            "role_id": "station_master",
            "station_code": "NDLS",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_breathalyzer_zero_tolerance(auth_headers):
    """Verifies Breathalyzer passed test and positive test interlocking lockout."""
    # 1. Clean Negative Test
    clean_test = {
        "staff_id": "LP-901",
        "staff_name": "Rajesh Pilot",
        "role": "loco_pilot",
        "train_no": "12004",
        "duty_type": "SIGN_ON",
        "reading_mg_100ml": 0.0,
    }
    resp1 = client.post("/api/workforce/breathalyzer", json=clean_test, headers=auth_headers)
    assert resp1.status_code == 200
    assert resp1.json()["passed"] is True
    assert resp1.json()["interlock_locked"] is False

    # 2. Positive Test (Zero Tolerance)
    failed_test = {
        "staff_id": "ALP-902",
        "staff_name": "Mukesh Assistant",
        "role": "alp",
        "train_no": "12004",
        "duty_type": "SIGN_ON",
        "reading_mg_100ml": 0.08,
    }
    resp2 = client.post("/api/workforce/breathalyzer", json=failed_test, headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["passed"] is False
    assert resp2.json()["interlock_locked"] is True

    # 3. Verify Sign-On is blocked for failed staff
    sign_on_req = {
        "crew_id": "ALP-902",
        "staff_name": "Mukesh Assistant",
        "role": "alp",
        "train_no": "12004",
        "station_code": "NDLS",
    }
    block_resp = client.post("/api/workforce/crew/sign-on", json=sign_on_req, headers=auth_headers)
    assert block_resp.status_code == 400
    assert "Positive Breathalyzer Lock" in block_resp.json()["detail"]


def test_crew_sign_on_sign_off_lifecycle(auth_headers):
    """Verifies normal crew sign-on, roster query, and sign-off with rest period calculation."""
    # 1. Sign On
    son_req = {
        "crew_id": "LP-901",
        "staff_name": "Rajesh Pilot",
        "role": "loco_pilot",
        "train_no": "12004",
        "station_code": "NDLS",
        "duty_hours_limit": 10.0,
    }
    son_resp = client.post("/api/workforce/crew/sign-on", json=son_req, headers=auth_headers)
    assert son_resp.status_code == 200
    roster_id = son_resp.json()["id"]

    # 2. Query Roster
    roster_resp = client.get("/api/workforce/crew/roster?station_code=NDLS", headers=auth_headers)
    assert roster_resp.status_code == 200
    crew_list = roster_resp.json()
    assert any(c["id"] == roster_id for c in crew_list)

    # 3. Sign Off
    soff_resp = client.post(f"/api/workforce/crew/{roster_id}/sign-off", headers=auth_headers)
    assert soff_resp.status_code == 200
    assert soff_resp.json()["status"] == "RESTING"
    assert soff_resp.json()["rest_hours_due"] in (12.0, 16.0)


def test_staff_shift_scheduler(auth_headers):
    """Verifies Shift scheduling and listing."""
    shift_req = {
        "staff_id": "usr-dysm-01",
        "staff_name": "Dy SM Evening",
        "role_id": "dy_sm",
        "station_code": "NDLS",
        "shift_date": "2026-08-29",
        "shift_type": "afternoon",
    }
    resp = client.post("/api/workforce/shifts", json=shift_req, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["shift_type"] == "afternoon"

    list_resp = client.get("/api/workforce/shifts?station_code=NDLS&shift_date=2026-08-29", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) > 0


def test_sahayak_porter_roster(auth_headers):
    """Verifies Sahayak roster query and duty toggling."""
    # 1. List Sahayak
    list_resp = client.get("/api/workforce/sahayak?station_code=NDLS", headers=auth_headers)
    assert list_resp.status_code == 200
    sahayaks = list_resp.json()
    assert len(sahayaks) > 0
    sk_id = sahayaks[0]["id"]

    # 2. Toggle Duty
    tog_resp = client.put(f"/api/workforce/sahayak/{sk_id}/duty", headers=auth_headers)
    assert tog_resp.status_code == 200
    assert "on_duty" in tog_resp.json()
