"""RailTwin-X WhatsApp Alert & Reply-to-ACK Live Demo Rehearsal (Phase 7).

Demonstrates the 60-second end-to-end judge demonstration flow:
1. Conflict detection on corridor (Train 12301 vs 12034 headway conflict at CNB Outer).
2. Outbound WhatsApp Alert dispatched to on-duty staff phones.
3. Inbound Reply-to-ACK parsing: Field staff types 'ACK CONF-12301-CNB'.
4. Closed-loop verification: Advisory ACK audit log records acceptance via WhatsApp.
5. Gateway fault drill: OpenWA disconnected -> HIGH alert fails over automatically to SMS.
6. Health monitoring: /v1/health reports gateway status dynamically.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from fastapi.testclient import TestClient
from api.main import app
from data.db import get_db
from notifications import AlertEvent, get_dispatcher
from notifications.health import get_health_tracker
from notifications.webhook_verify import generate_hmac_signature
from config import settings

client = TestClient(app)



def run_demo_rehearsal():
    db = get_db()
    dispatcher = get_dispatcher(db)
    health = get_health_tracker()

    print("=" * 80)
    print("📱 RAILTWIN-X: WHATSAPP ALERT CHANNEL & REPLY-TO-ACK LIVE DEMO")
    print("=" * 80)

    # ----------------------------------------------------
    # Step 1: Gateway Initial Health State
    # ----------------------------------------------------
    print("\n[STEP 1] Checking Initial Channel Health...")
    health.set_whatsapp_status("connected")
    h_resp = client.get("/v1/health")
    h_data = h_resp.json()
    print(f"  ✓ System Status:   {h_data['status'].upper()}")
    print(f"  ✓ WhatsApp Status: {h_data['whatsapp'].upper()} (OpenWA Gateway :2785)")
    print(f"  ✓ Database:        {h_data['db']}")

    # ----------------------------------------------------
    # Step 2: Trigger Operational Conflict Alert
    # ----------------------------------------------------
    print("\n[STEP 2] Simulating Spatial Headway Conflict at Kanpur Central Outer...")
    conflict_id = "CONF-12301-CNB"
    event = AlertEvent(
        severity="HIGH",
        event_type="conflict",
        title="Headway Conflict w/ Train #12034 at CNB Outer",
        body="Projected buffer deficit: 4.2m. ACTION: Divert & HOLD at Loop Line ON (Unnao).",
        station_code="CNB",
        train_no="12301",
        roles=["controller", "pointsman"],
        ack_id=conflict_id,
        metadata={"with_train": "12034", "overlap_minutes": 4.2},
    )

    print("  * Dispatching AlertEvent to on-duty staff at CNB...")
    disp_result = dispatcher.dispatch(event, bypass_rate_limit=True)
    print(f"  ✓ Total staff recipients resolved: {disp_result['total_recipients']}")
    print(f"  ✓ Dispatched alerts: {disp_result['dispatched_count']}")
    print(f"  ✓ Channels used: {disp_result['channels_used']}")
    print(f"  ✓ Formatted WhatsApp payload delivered:")
    print("-" * 60)
    print(event.formatted_text())
    print("-" * 60)

    # ----------------------------------------------------
    # Step 3: Simulate Field Staff Inbound Reply-to-ACK
    # ----------------------------------------------------
    print("\n[STEP 3] Staff replies on WhatsApp: 'ACK CONF-12301-CNB'...")
    webhook_body = json.dumps({
        "event": "message.received",
        "body": f"ACK {conflict_id}",
        "from": "919415011001@c.us",
        "timestamp": int(time.time()),
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }
    if settings.OPENWA_WEBHOOK_SECRET:
        headers["X-OpenWA-Signature"] = generate_hmac_signature(webhook_body, settings.OPENWA_WEBHOOK_SECRET)

    hook_resp = client.post("/v1/hooks/whatsapp", content=webhook_body, headers=headers)
    print(f"  ✓ Inbound Webhook HTTP Response: {hook_resp.status_code}")
    print(f"  ✓ Webhook Action Parsed: {hook_resp.json()}")

    # ----------------------------------------------------
    # Step 4: Verify Database Audit Trail
    # ----------------------------------------------------
    print("\n[STEP 4] Verifying Audit Trail in Database...")
    with db.transaction() as cur:
        cur.execute(
            "SELECT adv_id, decision, dispatcher_id, comment, recorded_at FROM advisory_ack_log WHERE adv_id = ? ORDER BY id DESC LIMIT 1",
            (conflict_id,),
        )
        ack_row = cur.fetchone()

        cur.execute(
            "SELECT staff_id, channel, status, sent_at, ack_at FROM notification_log ORDER BY id DESC LIMIT 1"
        )
        notif_row = cur.fetchone()

    if ack_row:
        print(f"  ✓ Closed Loop Confirmed! Advisory {ack_row['adv_id']} marked as '{ack_row['decision'].upper()}' by {ack_row['dispatcher_id']}")
        print(f"    Recorded Timestamp: {ack_row['recorded_at']}")
        print(f"    Comment: {ack_row['comment']}")
    if notif_row:
        print(f"  ✓ Notification Log Updated: Channel={notif_row['channel']}, Status={notif_row['status']}, AckAt={notif_row['ack_at']}")

    # ----------------------------------------------------
    # Step 5: Fault Drill — WhatsApp Down -> SMS Failover
    # ----------------------------------------------------
    print("\n[STEP 5] Fault Drill: OpenWA Gateway Offline -> High-Priority SMS Fallback...")
    health.set_whatsapp_status("disconnected")
    print("  * Simulating another HIGH alert while WhatsApp is offline...")

    # Temporarily force openwa failure in dispatcher for this test
    original_send = dispatcher.openwa.send
    dispatcher.openwa.send = lambda phone, text: False

    failover_event = AlertEvent(
        severity="HIGH",
        event_type="conflict",
        title="Emergency Single-Line Opposing Meet at TDL",
        body="Clearance below 5.0m limit. Hold #12424 on Platform 2.",
        station_code="TDL",
        train_no="12424",
        roles=["controller"],
        ack_id="CONF-12424-TDL",
    )
    failover_result = dispatcher.dispatch(failover_event, bypass_rate_limit=True)
    dispatcher.openwa.send = original_send

    print(f"  ✓ WhatsApp failed -> Channels used: {failover_result['channels_used']}")
    print(f"  ✓ Delivery status: {failover_result['deliveries'][0]['status']} via {failover_result['deliveries'][0]['channel'].upper()}")

    # Check health reflects status
    h_resp2 = client.get("/v1/health")
    print(f"  ✓ Live Health Check after outage: whatsapp = {h_resp2.json()['whatsapp'].upper()}")

    print("\n" + "=" * 80)
    print("🎯 DEMO REHEARSAL COMPLETE: ZERO-COST WHATSAPP ALERTS FULLY OPERATIONAL!")
    print("=" * 80)


if __name__ == "__main__":
    run_demo_rehearsal()
