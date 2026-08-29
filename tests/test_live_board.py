"""RailTwin-X Live Train Board Test Suite (Module A2).

Verifies computed live train arrival & departure board integration with ML ETA forecasts,
platform statuses, and actuals.
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


def test_live_board_query():
    """Verifies querying the live board for NDLS returns scheduled and expected trains."""
    token = create_access_token({"sub": "viewer", "role_id": "viewer"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/board/live?station_code=NDLS&kind=all", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["station_code"] == "NDLS"
    assert data["total_trains"] > 0
    assert "entries" in data

    first_train = data["entries"][0]
    assert "train_no" in first_train
    assert "train_name" in first_train
    assert "status" in first_train
    assert "status_color" in first_train
    assert "platform" in first_train
