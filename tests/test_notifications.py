"""Unit & Integration Tests for RailTwin-X WhatsApp & Notification System.

Verifies:
1. OpenWAChannel phone normalization, outbound HTTP calls, error handling.
2. SMSChannel fallback delivery and provider formatting.
3. NotificationDispatcher recipient resolution, rate-limiting, and failover logic.
4. HMAC-SHA256 inbound webhook security verification.
5. Inbound Reply-to-ACK parsing and advisory lifecycle closure.
6. /v1/health WhatsApp channel monitoring.
"""

from __future__ import annotations

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from config import settings
from data.db import get_db
from notifications.types import AlertEvent, StaffRecipient
from notifications.health import get_health_tracker
from notifications.channels.openwa import OpenWAChannel
from notifications.channels.sms import SMSChannel
from notifications.channels.inapp import InAppChannel
from notifications.dispatcher import NotificationDispatcher
from notifications.webhook_verify import verify_hmac, generate_hmac_signature

client = TestClient(app)


# ----------------------------------------------------
# 1. OpenWA Channel Tests
# ----------------------------------------------------
def test_openwa_phone_normalization():
    channel = OpenWAChannel()
    assert channel._normalize_phone("9876543210") == "919876543210"
    assert channel._normalize_phone("+91 98765 43210") == "919876543210"
    assert channel._normalize_phone("919876543210") == "919876543210"
    assert channel._normalize_phone("09876543210") == "919876543210"


def test_openwa_send_success():
    channel = OpenWAChannel(base_url="http://mock-openwa:2785", session_id="test-session")
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success = channel.send("9415011001", "Test message")
        assert success is True
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert "919415011001@c.us" in kwargs["json"]["chatId"]
        assert kwargs["json"]["text"] == "Test message"


def test_openwa_send_failure_updates_health():
    channel = OpenWAChannel(base_url="http://mock-openwa:2785", session_id="test-session")
    health = get_health_tracker()
    health.set_whatsapp_status("connected")

    with patch("httpx.Client.post", side_effect=Exception("Connection refused")):
        success = channel.send("9415011001", "Test message")
        assert success is False
        assert health.whatsapp_status == "down"


# ----------------------------------------------------
# 2. SMS Channel Tests
# ----------------------------------------------------
def test_sms_mock_send():
    sms = SMSChannel(provider="mock")
    assert sms.send("9415011001", "Emergency Alert") is True


def test_sms_invalid_phone():
    sms = SMSChannel(provider="mock")
    assert sms.send("123", "Alert") is False


# ----------------------------------------------------
# 3. HMAC Verification Tests
# ----------------------------------------------------
def test_hmac_verification_valid():
    secret = "secret-test-key-32chars-for-test"
    payload = b'{"event":"message.received","body":"ACK 123"}'
    signature = generate_hmac_signature(payload, secret)

    headers = {"X-OpenWA-Signature": signature}
    assert verify_hmac(payload, headers, secret) is True


def test_hmac_verification_invalid():
    secret = "secret-test-key-32chars-for-test"
    payload = b'{"event":"message.received","body":"ACK 123"}'
    headers = {"X-OpenWA-Signature": "sha256=invalid-signature-hex"}
    assert verify_hmac(payload, headers, secret) is False


def test_hmac_missing_header_when_secret_set():
    secret = "secret-test-key-32chars-for-test"
    payload = b'{"event":"message.received","body":"ACK 123"}'
    headers = {}
    assert verify_hmac(payload, headers, secret) is False


# ----------------------------------------------------
# 4. Notification Dispatcher Tests
# ----------------------------------------------------
def test_dispatcher_recipient_resolution():
    db = get_db()
    dispatcher = NotificationDispatcher(db)
    recipients = dispatcher.resolve_recipients(station_code="CNB", roles=["controller", "pointsman"])
    assert len(recipients) >= 2
    roles = {r.role for r in recipients}
    assert "controller" in roles or "pointsman" in roles


def test_dispatcher_rate_limiting():
    db = get_db()
    mock_openwa = MagicMock()
    mock_openwa.send.return_value = True

    dispatcher = NotificationDispatcher(db, openwa_channel=mock_openwa)

    event_medium = AlertEvent(
        severity="MEDIUM",
        event_type="advisory",
        title="Platform Swap Recommendation",
        body="Move 12424 to PF 5",
        station_code="CNB",
        roles=["controller"],
        ack_id="ADV-TEST-001",
    )

    # First dispatch succeeds
    res1 = dispatcher.dispatch(event_medium)
    assert res1["dispatched_count"] >= 1
    assert res1["deliveries"][0]["status"] == "wa_sent"

    # Immediate second medium dispatch is rate-limited
    res2 = dispatcher.dispatch(event_medium)
    assert res2["deliveries"][0]["status"] == "rate_limited"

    # HIGH severity alert bypasses rate limit
    event_high = AlertEvent(
        severity="HIGH",
        event_type="conflict",
        title="CRITICAL Headway Conflict",
        body="Hold immediately",
        station_code="CNB",
        roles=["controller"],
        ack_id="CONF-TEST-999",
    )
    res3 = dispatcher.dispatch(event_high)
    assert res3["deliveries"][0]["status"] == "wa_sent"


def test_dispatcher_failover_to_sms():
    db = get_db()
    mock_openwa = MagicMock()
    mock_openwa.send.return_value = False  # WhatsApp gateway down

    mock_sms = MagicMock()
    mock_sms.send.return_value = True

    dispatcher = NotificationDispatcher(db, openwa_channel=mock_openwa, sms_channel=mock_sms)

    event_high = AlertEvent(
        severity="HIGH",
        event_type="conflict",
        title="Emergency Single-Line Opposing Meet",
        body="Clearance deficit < 5m",
        station_code="CNB",
        roles=["controller"],
        ack_id="CONF-FAILOVER-01",
    )

    res = dispatcher.dispatch(event_high, bypass_rate_limit=True)
    assert res["dispatched_count"] >= 1
    assert "sms" in res["channels_used"]
    assert res["deliveries"][0]["channel"] == "sms"
    assert res["deliveries"][0]["status"] == "wa_failed_sms_sent"


# ----------------------------------------------------
# 5. Inbound Webhook End-to-End Tests
# ----------------------------------------------------
def test_webhook_session_status():
    health = get_health_tracker()
    health.set_whatsapp_status("down")

    payload = {"event": "session.status", "status": "connected"}
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.OPENWA_WEBHOOK_SECRET:
        headers["X-OpenWA-Signature"] = generate_hmac_signature(body, settings.OPENWA_WEBHOOK_SECRET)

    resp = client.post("/v1/hooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "status_updated"
    assert health.whatsapp_status == "connected"


def test_webhook_reply_ack_accepted():
    adv_id = "CONF-12301-CNB-TEST"
    payload = {
        "event": "message.received",
        "body": f"ACK {adv_id}",
        "from": "919415011001@c.us",
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.OPENWA_WEBHOOK_SECRET:
        headers["X-OpenWA-Signature"] = generate_hmac_signature(body, settings.OPENWA_WEBHOOK_SECRET)

    resp = client.post("/v1/hooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "accepted"
    assert data["adv_id"] == adv_id

    # Verify recorded in DB
    db = get_db()
    with db.transaction() as cur:
        cur.execute("SELECT decision, dispatcher_id FROM advisory_ack_log WHERE adv_id = ? ORDER BY id DESC LIMIT 1", (adv_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["decision"] == "accepted"
        assert row["dispatcher_id"] == "919415011001"


def test_webhook_reply_ack_rejected():
    adv_id = "CONF-12301-CNB-ESC"
    payload = {
        "event": "message.received",
        "body": f"ESC {adv_id}",
        "from": "919415011002@c.us",
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.OPENWA_WEBHOOK_SECRET:
        headers["X-OpenWA-Signature"] = generate_hmac_signature(body, settings.OPENWA_WEBHOOK_SECRET)

    resp = client.post("/v1/hooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "rejected"
    assert data["adv_id"] == adv_id


def test_health_reports_whatsapp():
    health = get_health_tracker()
    health.set_whatsapp_status("connected")

    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "whatsapp" in data
    assert data["whatsapp"] == "connected"
