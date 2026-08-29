"""RailTwin-X Platform Allocation Console Test Suite (Module A3).

Verifies platform state machines, blocking for maintenance, manual allocations with conflict interlocks,
and assignment locking.
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


def test_platform_blocking_and_conflicts():
    """Verifies maintenance blocking and assignment conflict rejection."""
    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    headers = {"Authorization": f"Bearer {sm_token}"}

    # 1. Block platform 5 for maintenance
    blk_res = client.post(
        "/api/platform/block",
        headers=headers,
        json={
            "station_code": "NDLS",
            "platform": 5,
            "state": "BLOCKED_MAINT",
            "reason": "Overhead traction line inspection",
        },
    )
    assert blk_res.status_code == 200
    assert blk_res.json()["state"] == "BLOCKED_MAINT"

    # 2. Attempt to assign a train to the blocked platform -> Must fail 400
    assign_fail = client.post(
        "/api/platform/assign",
        headers=headers,
        json={
            "station_code": "NDLS",
            "train_no": "12004",
            "run_date": "2026-08-28",
            "platform": 5,
            "assigned_arr": "10:00",
            "assigned_dep": "10:15",
            "is_locked": True,
        },
    )
    assert assign_fail.status_code == 400
    assert "BLOCKED_MAINT" in assign_fail.json()["detail"]

    # 3. Release platform 5
    rel_res = client.post(
        "/api/platform/block",
        headers=headers,
        json={"station_code": "NDLS", "platform": 5, "state": "FREE"},
    )
    assert rel_res.status_code == 200

    # 4. Now assign train to platform 5 -> Should succeed
    assign_ok = client.post(
        "/api/platform/assign",
        headers=headers,
        json={
            "station_code": "NDLS",
            "train_no": "12004",
            "run_date": "2026-08-28",
            "platform": 5,
            "assigned_arr": "10:00",
            "assigned_dep": "10:15",
            "is_locked": True,
        },
    )
    assert assign_ok.status_code == 201
    assign_id = assign_ok.json()["id"]

    # 5. Overlapping train assignment -> Must fail 409 Conflict
    overlap_fail = client.post(
        "/api/platform/assign",
        headers=headers,
        json={
            "station_code": "NDLS",
            "train_no": "12002",
            "run_date": "2026-08-28",
            "platform": 5,
            "assigned_arr": "10:05",  # Overlaps 10:00-10:15!
            "assigned_dep": "10:20",
            "is_locked": False,
        },
    )
    assert overlap_fail.status_code == 409
    assert "Conflict" in overlap_fail.json()["detail"]

    # 6. Toggle assignment lock
    lock_res = client.post(
        f"/api/platform/assignments/{assign_id}/lock",
        headers=headers,
        json={"is_locked": False},
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["is_locked"] is False
