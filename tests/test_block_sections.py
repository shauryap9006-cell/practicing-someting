"""RailTwin-X Block Section & Line Status Test Suite (Module A5).

Verifies corridor block status queries, state updates, Line Clear grant workflows,
and Speed Restriction (TSR) caution overlays.
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


def test_block_section_lifecycle():
    """Verifies block statuses, Line Clear grants, and block state transitions."""
    sec_ctrl_token = create_access_token({"sub": "section_ctrl", "role_id": "section_controller"})
    headers = {"Authorization": f"Bearer {sec_ctrl_token}"}

    # 1. Fetch block statuses
    res = client.get("/api/blocks/status?station_code=NDLS", headers=headers)
    assert res.status_code == 200
    blocks = res.json()
    assert len(blocks) > 0
    blk = blocks[0]
    b_id = blk["block_id"]

    # 2. Grant Line Clear
    lc_res = client.post(
        f"/api/blocks/{b_id}/line-clear",
        headers=headers,
        json={"train_no": "12004", "notes": "Line Clear Authority No. 402"},
    )
    assert lc_res.status_code == 200
    assert lc_res.json()["status"] == "LINE_CLEAR_GRANTED"

    # 3. Update block state to CLEAR
    clr_res = client.post(
        f"/api/blocks/{b_id}/state",
        headers=headers,
        json={"state": "CLEAR", "notes": "Train cleared block section"},
    )
    assert clr_res.status_code == 200
    assert clr_res.json()["state"] == "CLEAR"
