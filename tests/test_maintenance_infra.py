"""Phase 5 Maintenance & Infrastructure Engineering Test Suite.

Tests:
- G1: Rake Health & BPC Register
- G2: Fixed Asset Directory & Work Orders Lifecycle
- G3: Cleanliness & Bio-Toilet Feedback Logging
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Creates authorized JWT headers for testing infrastructure routes."""
    token = create_access_token(
        data={
            "sub": "sm_ndls",
            "username": "sm_ndls",
            "role_id": "station_master",
            "station_code": "NDLS",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_rake_bpc_lifecycle(auth_headers):
    """Verifies Rake & BPC certificate registration and query."""
    rake_req = {
        "rake_id": "RAKE-12004-Z",
        "train_no": "12004",
        "bpc_number": "BPC-NR-2026-999",
        "bpc_issue_date": "2026-08-28",
        "bpc_valid_until": "2026-09-04",
        "bpc_type": "PREMIUM",
        "brake_power_percent": 100.0,
        "air_brake_pressure_kg": 5.0,
        "coach_count": 20,
    }
    resp = client.post("/api/infrastructure/rakes", json=rake_req, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    list_resp = client.get("/api/infrastructure/rakes?train_no=12004", headers=auth_headers)
    assert list_resp.status_code == 200
    rakes = list_resp.json()
    assert any(r["rake_id"] == "RAKE-12004-Z" for r in rakes)


def test_fixed_assets_and_work_orders(auth_headers):
    """Verifies Fixed Asset registration, work order logging, and resolution."""
    # 1. Register Asset
    asset_req = {
        "asset_tag": "SIG-NDLS-99",
        "asset_type": "SIGNAL",
        "station_code": "NDLS",
        "platform_or_track": "Main Line South",
        "last_serviced_date": "2026-08-01",
        "next_service_due": "2026-09-01",
    }
    resp = client.post("/api/infrastructure/assets", json=asset_req, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPERATIONAL"

    # 2. Log Work Order (Defect)
    wo_req = {
        "asset_tag": "SIG-NDLS-99",
        "station_code": "NDLS",
        "issue_description": "Red aspect LED filament burnt out",
        "priority": "URGENT",
    }
    wo_resp = client.post("/api/infrastructure/work-orders", json=wo_req, headers=auth_headers)
    assert wo_resp.status_code == 200
    wo_id = wo_resp.json()["id"]
    assert wo_resp.json()["status"] == "OPEN"

    # 3. Resolve Work Order
    res_resp = client.put(
        f"/api/infrastructure/work-orders/{wo_id}/resolve",
        json={"resolution_notes": "Replaced LED signal unit and tested with interlocking relay"},
        headers=auth_headers,
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RESOLVED"


def test_cleanliness_inspection_logging(auth_headers):
    """Verifies Cleanliness inspection scores."""
    clean_req = {
        "station_code": "NDLS",
        "area_type": "PLATFORM",
        "platform_number": 1,
        "score_1_to_5": 5,
        "contractor_name": "Swachh Rail Agency",
        "notes": "Mechanized floor scrubbing completed",
    }
    resp = client.post("/api/infrastructure/cleaning-logs", json=clean_req, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["score"] == 5

    list_resp = client.get("/api/infrastructure/cleaning-logs?station_code=NDLS", headers=auth_headers)
    assert list_resp.status_code == 200
    logs = list_resp.json()
    assert len(logs) > 0
