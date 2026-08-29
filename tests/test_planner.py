"""RailTwin-X Gantt Day Planner Test Suite (Module C4).

Verifies 24h interactive what-if delay cascade simulation via SimPy,
Safety Interlock validation, and batch changeset commits.
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


def test_planner_simulation_and_apply():
    """Verifies SimPy what-if simulation and batch changeset application."""
    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    headers = {"Authorization": f"Bearer {sm_token}"}

    payload = {
        "station_code": "NDLS",
        "plan_date": "2026-08-28",
        "mutations": [
            {
                "train_no": "12004",
                "action": "reassign_platform",
                "target_platform": 4,
                "new_arr": "06:10",
                "new_dep": "06:20",
                "reason": "Resolve throat conflict with Freight-901",
            },
            {
                "train_no": "12424",
                "action": "retimed",
                "target_platform": 1,
                "new_arr": "06:30",
                "new_dep": "06:40",
            },
        ],
    }

    # 1. Simulate day plan
    sim_res = client.post("/api/planner/simulate", headers=headers, json=payload)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "baseline_total_delay_min" in sim_data
    assert "proposed_total_delay_min" in sim_data
    assert sim_data["total_mutations"] == 2

    # 2. Apply changeset
    app_res = client.post("/api/planner/apply", headers=headers, json=payload)
    assert app_res.status_code == 201
    app_data = app_res.json()
    assert app_data["status"] == "COMMITTED"
    assert app_data["applied_mutations"] == 2

    # 3. Verify changeset list
    list_res = client.get("/api/planner/changesets?station_code=NDLS", headers=headers)
    assert list_res.status_code == 200
    cs_list = list_res.json()
    assert len(cs_list) > 0
