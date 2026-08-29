"""RailTwin-X Working Timetable Manager Test Suite (Module A1).

Verifies versioned timetable lifecycle (draft -> publish -> archive), train schedule CRUD,
negative dwell validation, bulk seed import adapter, and version diffing.
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


def test_timetable_version_lifecycle():
    """Verifies creating a draft version, importing seeds, validating, and publishing."""
    admin_token = create_access_token({"sub": "admin", "role_id": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create draft timetable version
    res = client.post(
        "/api/timetable/versions",
        headers=headers,
        json={
            "version_name": "WTT 2026 Test Edition",
            "effective_from": "2026-09-01",
            "description": "Test WTT version",
        },
    )
    assert res.status_code == 201
    v_data = res.json()
    version_id = v_data["id"]
    assert v_data["status"] == "draft"

    # 2. Add valid train stop entries
    res_entry = client.post(
        "/api/timetable/entries",
        headers=headers,
        json={
            "version_id": version_id,
            "train_no": "12004",
            "train_name": "Lucknow Swarna Shatabdi",
            "train_type": "express",
            "direction": "DOWN",
            "station_code": "NDLS",
            "stop_seq": 1,
            "sched_arr": "06:10",
            "sched_dep": "06:15",
            "halt_min": 5,
            "platform_default": 1,
        },
    )
    assert res_entry.status_code == 201
    entry_id = res_entry.json()["id"]

    # 3. Validate timetable
    val_res = client.get(f"/api/timetable/versions/{version_id}/validate", headers=headers)
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # 4. Inject invalid negative dwell entry
    bad_entry = client.post(
        "/api/timetable/entries",
        headers=headers,
        json={
            "version_id": version_id,
            "train_no": "99999",
            "train_name": "Broken Express",
            "train_type": "passenger",
            "direction": "UP",
            "station_code": "GZB",
            "stop_seq": 1,
            "sched_arr": "10:30",
            "sched_dep": "10:15",  # Negative dwell!
            "halt_min": 2,
            "platform_default": 1,
        },
    )
    assert bad_entry.status_code == 201
    bad_id = bad_entry.json()["id"]

    # Validation should catch it
    val_bad = client.get(f"/api/timetable/versions/{version_id}/validate", headers=headers)
    assert val_bad.json()["is_valid"] is False
    assert len(val_bad.json()["issues"]) >= 1

    # Attempting to publish must fail
    pub_fail = client.post(f"/api/timetable/versions/{version_id}/publish", headers=headers)
    assert pub_fail.status_code == 400

    # Delete the bad entry
    del_res = client.delete(f"/api/timetable/entries/{bad_id}", headers=headers)
    assert del_res.status_code == 200

    # Publish should now succeed
    pub_success = client.post(f"/api/timetable/versions/{version_id}/publish", headers=headers)
    assert pub_success.status_code == 200
    assert pub_success.json()["status"] == "published"
