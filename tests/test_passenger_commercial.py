"""Phase 3 Passenger Experience & Commercial Services Test Suite.

Tests:
- E1: Delay Certificate Issuance & QR Token Verification
- E2: Multilingual 3-Language Platform Announcement Engine
- E3: Commercial Lease & Stall Directory
- E4: Passenger Lost & Found Registry & Claim Workflow
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Creates authorized JWT headers for testing commercial routes."""
    token = create_access_token(
        data={
            "sub": "sm_ndls",
            "username": "sm_ndls",
            "role_id": "station_master",
            "station_code": "NDLS",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_delay_certificate_lifecycle(auth_headers):
    """Verifies Delay Certificate generation, printable retrieval, and QR cryptographic verification."""
    # 1. Issue Delay Certificate
    cert_req = {
        "train_no": "12004",
        "station_code": "NDLS",
        "pnr_no": "2489102931",
        "issued_to_name": "Rohan Sharma",
        "reason": "OHE maintenance delay at Ghaziabad outer",
    }
    resp = client.post("/api/commercial/delay-certificate", json=cert_req, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    cert_no = data["cert_no"]
    qr_token = data["qr_token"]
    assert "IR-DC-NDLS-" in cert_no
    assert data["issued_to_name"] == "Rohan Sharma"
    assert data["delay_min"] >= 0

    # 2. Get Certificate by cert_no
    get_resp = client.get(f"/api/commercial/delay-certificate/{cert_no}")
    assert get_resp.status_code == 200
    assert get_resp.json()["cert_no"] == cert_no

    # 3. Public QR Verification
    verify_resp = client.get(f"/api/commercial/delay-certificate/verify/{qr_token}")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True
    assert "Authentic" in verify_resp.json()["message"]


def test_multilingual_announcement_generation():
    """Verifies Indian Railways 3-Language announcement text generation."""
    resp = client.get("/api/commercial/announcements/generate?train_no=12004&station_code=NDLS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "12004"
    assert "languages" in data
    assert "english" in data["languages"]
    assert "hindi" in data["languages"]
    assert "regional" in data["languages"]
    assert "12004" in data["languages"]["english"]["text"]
    assert "12004" in data["languages"]["hindi"]["text"]


def test_commercial_stalls_directory(auth_headers):
    """Verifies Commercial Stall registration and query."""
    # 1. Register Stall
    stall_req = {
        "stall_code": "STALL-NDLS-PF1-99",
        "station_code": "NDLS",
        "platform_number": 1,
        "stall_type": "TEA_STALL",
        "vendor_name": "Chai Point Express",
        "contact_phone": "+919876543299",
        "monthly_rent_inr": 30000.0,
        "lease_start_date": "2026-01-01",
        "lease_expiry_date": "2029-01-01",
    }
    resp = client.post("/api/commercial/stalls", json=stall_req, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # 2. List Stalls
    list_resp = client.get("/api/commercial/stalls?station_code=NDLS", headers=auth_headers)
    assert list_resp.status_code == 200
    stalls = list_resp.json()
    assert any(s["stall_code"] == "STALL-NDLS-PF1-99" for s in stalls)


def test_lost_and_found_workflow(auth_headers):
    """Verifies Lost & Found registration, listing, and passenger claim workflow."""
    # 1. Register Lost Item
    item_req = {
        "item_type": "ELECTRONICS",
        "description": "Black Dell Laptop Bag with charger and documents",
        "found_location": "Platform 1 Waiting Hall Seat 14",
        "station_code": "NDLS",
        "train_no": "12424",
    }
    resp = client.post("/api/commercial/lost-found", json=item_req, headers=auth_headers)
    assert resp.status_code == 200
    item_id = resp.json()["id"]
    assert resp.json()["status"] == "UNCLAIMED"

    # 2. Query Unclaimed Items
    list_resp = client.get("/api/commercial/lost-found?station_code=NDLS&status=UNCLAIMED", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(i["id"] == item_id for i in items)

    # 3. Claim Item
    claim_req = {
        "claimant_name": "Amit Kumar",
        "claimant_id_proof": "Aadhaar XXXX-XXXX-1234",
        "claimant_phone": "+919811223344",
    }
    claim_resp = client.put(f"/api/commercial/lost-found/{item_id}/claim", json=claim_req, headers=auth_headers)
    assert claim_resp.status_code == 200
    assert claim_resp.json()["status"] == "CLAIMED"
    assert claim_resp.json()["claimant_name"] == "Amit Kumar"
