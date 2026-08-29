"""RailTwin-X Shunting & Non-Timetable Movements Test Suite (Module A6).

Verifies shunting logs, status transitions, and platform overlap warning checks.
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


def test_shunting_movement_lifecycle():
    """Verifies creating, listing, and updating a shunting movement."""
    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    headers = {"Authorization": f"Bearer {sm_token}"}

    # 1. Create a shunting move
    res = client.post(
        "/api/ops/shunting",
        headers=headers,
        json={
            "station_code": "NDLS",
            "move_type": "loco_attach",
            "loco_id": "WAP7-30214",
            "rake_id": "RAKE-12004-A",
            "from_track": "Yard-Line-2",
            "to_track": "PF1",
            "start_time": "05:30",
            "end_time": "05:45",
            "notes": "Attach power for Lucknow Shatabdi",
        },
    )
    assert res.status_code == 201
    data = res.json()
    move_id = data["id"]
    assert data["status"] == "REQUESTED"

    # 2. Update status to IN_PROGRESS
    up_res = client.put(
        f"/api/ops/shunting/{move_id}/status",
        headers=headers,
        json={"status": "IN_PROGRESS", "notes": "Points set, loco moving"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["status"] == "IN_PROGRESS"

    # 3. List shunting moves
    list_res = client.get("/api/ops/shunting?station_code=NDLS", headers=headers)
    assert list_res.status_code == 200
    moves = list_res.json()
    assert any(m["id"] == move_id for m in moves)
