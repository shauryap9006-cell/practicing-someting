"""RailTwin-X Ground Truth Set-In / Set-Out Test Suite (Module A4).

Verifies one-tap human arrival & departure confirmations, platform state transitions,
discrepancy tracking against predicted ETAs, and ground truth ad_events logging.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import get_db
from data.seed_users import seed_roles_and_users

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    db = get_db()
    seed_roles_and_users(db)


def test_set_in_and_set_out_workflow():
    """Verifies train arrival (Set-In) and departure (Set-Out) lifecycle."""
    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    headers = {"Authorization": f"Bearer {sm_token}"}

    # 1. Record Set-In
    res_in = client.post(
        "/api/ops/setin/12004",
        headers=headers,
        json={
            "station_code": "NDLS",
            "platform": 3,
            "actual_ts": "2026-08-28T06:12:00Z",
            "predicted_ts": "2026-08-28T06:10:00Z",
        },
    )
    assert res_in.status_code == 200
    in_data = res_in.json()
    assert in_data["status"] == "ARRIVED"
    assert in_data["platform"] == 3
    assert in_data["discrepancy_min"] == 2.0

    # Verify platform state is now OCCUPIED
    pf_res = client.get("/api/platform/states?station_code=NDLS", headers=headers)
    assert pf_res.status_code == 200
    pf3 = next(p for p in pf_res.json() if p["platform"] == 3)
    assert pf3["state"] == "OCCUPIED"
    assert pf3["occupied_by_train"] == "12004"

    # 2. Record Set-Out
    res_out = client.post(
        "/api/ops/setout/12004",
        headers=headers,
        json={
            "station_code": "NDLS",
            "platform": 3,
            "actual_ts": "2026-08-28T06:20:00Z",
        },
    )
    assert res_out.status_code == 200
    out_data = res_out.json()
    assert out_data["status"] == "DEPARTED"

    # Verify platform state is released to FREE
    pf_res2 = client.get("/api/platform/states?station_code=NDLS", headers=headers)
    pf3_after = next(p for p in pf_res2.json() if p["platform"] == 3)
    assert pf3_after["state"] == "FREE"
    assert pf3_after["occupied_by_train"] is None

    # 3. Query historical ad_events
    events_res = client.get("/api/ops/ad-events?station_code=NDLS&train_no=12004", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 2
    assert any(e["event_kind"] == "setin" for e in events)
    assert any(e["event_kind"] == "setout" for e in events)
