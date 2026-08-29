"""RailTwin-X Digital Shift Handover Logbook Test Suite (Module I2).

Verifies auto-aggregation of open operational registers, dual digital signature workflows,
and status transitions from draft -> signed -> acknowledged.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import Database, get_db

client = TestClient(app)


def test_handover_current_summary():
    """Verifies that current handover summary returns auto-collected operational data."""
    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master", "station_code": "NDLS"})
    response = client.get(
        "/api/handover/current?station_code=NDLS",
        headers={"Authorization": f"Bearer {sm_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["station_code"] == "NDLS"
    assert "active_srs" in data
    assert "open_incidents" in data
    assert "suggested_shift" in data


def test_handover_full_signature_lifecycle():
    """Verifies complete lifecycle: Draft -> Outgoing Sign -> Incoming Acknowledgment."""
    sm_out_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master", "station_code": "NDLS"})
    sm_in_token = create_access_token({"sub": "dysm_ndls", "role_id": "dy_sm", "station_code": "NDLS"})

    # 1. Create draft
    draft_resp = client.post(
        "/api/handover/draft",
        json={
            "station_code": "NDLS",
            "shift_date": "2026-08-28",
            "shift_type": "morning",
            "operational_notes": "Platform 3 track circuit inspection scheduled at 14:00.",
        },
        headers={"Authorization": f"Bearer {sm_out_token}"},
    )
    assert draft_resp.status_code == 201
    handover = draft_resp.json()
    handover_id = handover["id"]
    assert handover["status"] == "draft"

    # 2. Outgoing sign-out
    sign_resp = client.post(
        f"/api/handover/{handover_id}/sign-out",
        json={"operational_notes": "Platform 3 track circuit inspection scheduled at 14:00. All clear."},
        headers={"Authorization": f"Bearer {sm_out_token}"},
    )
    assert sign_resp.status_code == 200
    assert sign_resp.json()["status"] == "signed"
    assert sign_resp.json()["outgoing_signed_at"] is not None

    # 3. Incoming acknowledgment
    ack_resp = client.post(
        f"/api/handover/{handover_id}/ack-in",
        json={"acknowledgment_notes": "Shift received. Monitoring PF3."},
        headers={"Authorization": f"Bearer {sm_in_token}"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"
    assert ack_resp.json()["incoming_acked_at"] is not None


def test_handover_ack_before_sign_rejected():
    """Verifies that an incoming staff member cannot acknowledge an unsigned draft."""
    sm_out_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master", "station_code": "NDLS"})
    sm_in_token = create_access_token({"sub": "dysm_ndls", "role_id": "dy_sm", "station_code": "NDLS"})

    # Create draft
    draft_resp = client.post(
        "/api/handover/draft",
        json={
            "station_code": "NDLS",
            "shift_date": "2026-08-29",
            "shift_type": "night",
            "operational_notes": "Night maintenance.",
        },
        headers={"Authorization": f"Bearer {sm_out_token}"},
    )
    handover_id = draft_resp.json()["id"]

    # Try acknowledging without signing
    ack_resp = client.post(
        f"/api/handover/{handover_id}/ack-in",
        json={"acknowledgment_notes": "Early ack."},
        headers={"Authorization": f"Bearer {sm_in_token}"},
    )
    assert ack_resp.status_code == 400
    assert "cannot be acknowledged before outgoing Station Master signs" in ack_resp.json()["detail"]
