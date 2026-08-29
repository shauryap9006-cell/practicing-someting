"""RailTwin-X Notification Center & Escalation Ladder Test Suite (Module I4).

Verifies role-targeted alert dispatch, in-app notification queries, one-click acknowledgment,
and the automated 5-minute escalation ladder for critical alerts.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import Database, get_db
from notifications.dispatcher import (
    acknowledge_notification,
    escalate_unacked_notifications,
    notify,
)

client = TestClient(app)


def test_notify_helper_and_active_query():
    """Verifies that notify() inserts active alert and API returns it."""
    db = get_db()
    notif = notify(
        event_type="TEST_TSR_ALERT",
        target_roles=["station_master"],
        severity="warning",
        title="Speed Restriction at KM 45",
        message="Temporary caution order 30 km/h active.",
        payload={"km": 45, "speed": 30},
        db=db,
    )
    assert notif["notification_id"] > 0

    sm_token = create_access_token({"sub": "sm_ndls", "role_id": "station_master"})
    resp = client.get(
        "/api/notifications/active",
        headers={"Authorization": f"Bearer {sm_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["id"] == notif["notification_id"] for i in items)


def test_notification_ack_flow():
    """Verifies that acknowledging an alert updates its state and removes from active list."""
    db = get_db()
    notif = notify(
        event_type="TEST_CREW_ALERT",
        target_roles=["crew_controller"],
        severity="info",
        title="Crew Shift Change",
        message="Crew arriving at NDLS Platform 1.",
        db=db,
    )
    notif_id = notif["notification_id"]

    crew_token = create_access_token({"sub": "crew_ctrl", "role_id": "crew_controller"})
    ack_resp = client.post(
        f"/api/notifications/{notif_id}/ack",
        json={"channel": "in_app", "notes": "Noted"},
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["state"] == "acked"


def test_escalation_ladder_trigger():
    """Verifies that unacknowledged critical notifications older than threshold are escalated."""
    db = get_db()
    # Insert old unacked critical notification
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO notifications (
                event_type, target_role, severity, title, message, payload_json, state, created_at
            ) VALUES ('UNACKED_SIGNAL_FAULT', 'engineer', 'critical', 'Signal Fault Track 4', 'Immediate fix required', '{}', 'sent', ?);
            """,
            (old_time,),
        )
        notif_id = cur.lastrowid

    # Run escalation
    escalated = escalate_unacked_notifications(max_age_minutes=5, db=db)
    assert any(e["id"] == notif_id for e in escalated)

    # Check that state is updated to escalated in DB
    with db.transaction() as cur:
        cur.execute("SELECT state, escalated_at FROM notifications WHERE id = ?;", (notif_id,))
        row = cur.fetchone()
        assert row["state"] == "escalated"
        assert row["escalated_at"] is not None
