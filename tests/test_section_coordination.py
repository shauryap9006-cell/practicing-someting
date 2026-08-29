"""Phase 6 Multi-Station Topology & Section Coordination Test Suite.

Tests:
- C3: Corridor Topology & Inter-Station Cross-Locking Handoff Protocol
- C2: Dynamic Precedence & Overtake Advisory Engine
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Creates authorized JWT headers for testing section routes."""
    token = create_access_token(
        data={
            "sub": "section_ctrl",
            "username": "section_ctrl",
            "role_id": "section_controller",
            "station_code": "NDLS",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_corridor_topology(auth_headers):
    """Verifies retrieval of multi-station corridor topological graph."""
    resp = client.get("/api/section/corridor", headers=auth_headers)
    assert resp.status_code == 200
    sections = resp.json()
    assert len(sections) > 0
    assert any(s["from_station"] == "NDLS" and s["to_station"] == "GZB" for s in sections)


def test_cross_station_handoff_lifecycle(auth_headers):
    """Verifies inter-station slot reservation and Line Clear handshake."""
    # 1. Request Handoff
    req_payload = {
        "section_id": "SEC-NDLS-GZB",
        "from_station": "NDLS",
        "to_station": "GZB",
        "train_no": "12004",
        "notes": "Express entry request",
    }
    req_resp = client.post("/api/section/handoff/request", json=req_payload, headers=auth_headers)
    assert req_resp.status_code == 200
    lock_id = req_resp.json()["id"]
    assert req_resp.json()["status"] == "REQUESTED"

    # 2. Grant Handoff
    grant_resp = client.put(f"/api/section/handoff/{lock_id}/grant", headers=auth_headers)
    assert grant_resp.status_code == 200
    assert grant_resp.json()["status"] == "GRANTED"

    # 3. Release Handoff
    rel_resp = client.put(f"/api/section/handoff/{lock_id}/release", headers=auth_headers)
    assert rel_resp.status_code == 200
    assert rel_resp.json()["status"] == "RELEASED"


def test_dynamic_precedence_advisories(auth_headers):
    """Verifies dynamic precedence calculation and execution."""
    # 1. Generate Advisories
    gen_resp = client.get("/api/section/advisories/generate?section_id=SEC-NDLS-GZB", headers=auth_headers)
    assert gen_resp.status_code == 200
    advisories = gen_resp.json()
    assert len(advisories) > 0
    adv_id = advisories[0]["id"]
    assert "OVERTAKE" in [a["advisory_type"] for a in advisories]

    # 2. Execute Precedence Advisory
    exec_resp = client.post(f"/api/section/advisories/{adv_id}/execute", headers=auth_headers)
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "EXECUTED"
