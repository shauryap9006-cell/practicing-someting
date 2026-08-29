"""RailTwin-X Central Notification Dispatcher & Escalation Engine (Module I4).

Routes AlertEvents to targeted on-duty field staff and controllers, maintains the in-app
notification center in SQLite, executes the 5-minute escalation ladder for unacknowledged
critical alerts, and provides the global `notify()` event bus helper.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from config import settings
from data.audit import record_audit
from data.db import Database, get_db
from notifications.channels.inapp import InAppChannel
from notifications.channels.openwa import OpenWAChannel
from notifications.channels.sms import SMSChannel
from notifications.types import AlertEvent, StaffRecipient

ALLOWED_TEST_NUMBERS = {"9580873724", "9569890921"}
MAIN_CONTROLLER_PHONE = "9580873724"
FIELD_STAFF_PHONE = "9569890921"


class NotificationDispatcher:
    """Central routing, dispatch, and escalation engine for railway operational alerts."""

    def __init__(
        self,
        db: Optional[Database] = None,
        openwa_channel: Optional[OpenWAChannel] = None,
        sms_channel: Optional[SMSChannel] = None,
        inapp_channel: Optional[InAppChannel] = None,
    ):
        self.db = db or get_db()
        self.openwa = openwa_channel or OpenWAChannel()
        self.sms = sms_channel or SMSChannel()
        self.inapp = inapp_channel or InAppChannel(self.db)
        self._last_sent_map: Dict[str, float] = {}

    def resolve_recipients(
        self,
        station_code: str,
        roles: List[str],
    ) -> List[StaffRecipient]:
        """Queries on-duty staff at station matching target roles, enforcing test whitelist."""
        stn = station_code.upper() if station_code else "CNB"
        roles_lower = [r.lower() for r in roles]

        with self.db.transaction() as cur:
            if roles_lower:
                placeholders = ",".join("?" for _ in roles_lower)
                cur.execute(
                    f"""
                    SELECT staff_id, name, role, phone, station_code, on_duty
                    FROM staff
                    WHERE station_code = ? AND role IN ({placeholders}) AND on_duty = 1
                    """,
                    (stn, *roles_lower),
                )
            else:
                cur.execute(
                    """
                    SELECT staff_id, name, role, phone, station_code, on_duty
                    FROM staff
                    WHERE station_code = ? AND on_duty = 1
                    """,
                    (stn,),
                )
            rows = cur.fetchall()

        raw_recipients = [
            StaffRecipient(
                staff_id=r["staff_id"],
                name=r["name"],
                role=r["role"],
                phone=r["phone"],
                station_code=r["station_code"],
                on_duty=bool(r["on_duty"]),
            )
            for r in rows
        ]

        if not raw_recipients:
            raw_recipients = [
                StaffRecipient(
                    staff_id="STF-CNB-01",
                    name="Section Controller",
                    role="controller",
                    phone=MAIN_CONTROLLER_PHONE,
                    station_code="CNB",
                    on_duty=True,
                ),
                StaffRecipient(
                    staff_id="STF-CNB-02",
                    name="Station Controller",
                    role="controller",
                    phone=FIELD_STAFF_PHONE,
                    station_code="CNB",
                    on_duty=True,
                ),
            ]

        filtered_recipients: List[StaffRecipient] = []
        seen_phones = set()

        for s in raw_recipients:
            target_phone = s.phone
            if target_phone not in ALLOWED_TEST_NUMBERS:
                target_phone = MAIN_CONTROLLER_PHONE if "controller" in s.role.lower() else FIELD_STAFF_PHONE

            if target_phone not in seen_phones and target_phone in ALLOWED_TEST_NUMBERS:
                seen_phones.add(target_phone)
                filtered_recipients.append(
                    StaffRecipient(
                        staff_id=s.staff_id,
                        name=s.name,
                        role=s.role,
                        phone=target_phone,
                        station_code=s.station_code,
                        on_duty=s.on_duty,
                    )
                )

        return filtered_recipients

    def _is_rate_limited(self, staff_id: str, severity: str, bypass_rate_limit: bool = False) -> bool:
        if bypass_rate_limit or severity.upper() in ("HIGH", "CRITICAL"):
            return False
        last_time = self._last_sent_map.get(staff_id, 0.0)
        window_seconds = settings.NOTIFICATION_RATE_LIMIT_MINUTES * 60.0
        return (time.time() - last_time) < window_seconds

    def dispatch(
        self,
        event: AlertEvent,
        bypass_rate_limit: bool = False,
    ) -> Dict[str, Any]:
        """Dispatches AlertEvent to all resolved staff with channel failover & audit logging."""
        recipients = self.resolve_recipients(event.station_code, event.roles)
        results = []
        channels_used: Set[str] = set()

        for staff in recipients:
            if self._is_rate_limited(staff.staff_id, event.severity, bypass_rate_limit):
                self.inapp.log_dispatch(staff, event, "rate_limited", "skipped_rate_limit")
                results.append({
                    "staff_id": staff.staff_id,
                    "name": staff.name,
                    "phone": staff.phone,
                    "status": "rate_limited",
                    "channel": None,
                })
                continue

            message_text = event.formatted_text(staff.name)
            wa_success = False

            try:
                wa_success = self.openwa.send(staff.phone, message_text)
            except Exception:
                wa_success = False

            if wa_success:
                status = "wa_sent"
                channel = "whatsapp"
                channels_used.add("whatsapp")
                self._last_sent_map[staff.staff_id] = time.time()
                self.inapp.log_dispatch(staff, event, channel, status)
                results.append({
                    "staff_id": staff.staff_id,
                    "name": staff.name,
                    "phone": staff.phone,
                    "status": status,
                    "channel": channel,
                })
            else:
                if event.severity.upper() in ("HIGH", "CRITICAL"):
                    sms_success = False
                    try:
                        sms_success = self.sms.send(staff.phone, message_text)
                    except Exception:
                        sms_success = False

                    status = "wa_failed_sms_sent" if sms_success else "wa_and_sms_failed"
                    channel = "sms"
                    channels_used.add("sms")
                    self._last_sent_map[staff.staff_id] = time.time()
                    self.inapp.log_dispatch(staff, event, channel, status)
                    results.append({
                        "staff_id": staff.staff_id,
                        "name": staff.name,
                        "phone": staff.phone,
                        "status": status,
                        "channel": channel,
                    })
                else:
                    status = "wa_failed_no_fallback"
                    channel = "whatsapp"
                    self.inapp.log_dispatch(staff, event, channel, status)
                    results.append({
                        "staff_id": staff.staff_id,
                        "name": staff.name,
                        "phone": staff.phone,
                        "status": status,
                        "channel": channel,
                    })

        return {
            "event_type": event.event_type,
            "severity": event.severity,
            "title": event.title,
            "station_code": event.station_code,
            "total_recipients": len(recipients),
            "dispatched_count": len([r for r in results if "sent" in r["status"]]),
            "channels_used": list(channels_used),
            "deliveries": results,
        }


_GLOBAL_DISPATCHER: Optional[NotificationDispatcher] = None


def get_dispatcher(db: Optional[Database] = None) -> NotificationDispatcher:
    global _GLOBAL_DISPATCHER
    if _GLOBAL_DISPATCHER is None:
        _GLOBAL_DISPATCHER = NotificationDispatcher(db or get_db())
    return _GLOBAL_DISPATCHER


def notify(
    event_type: str,
    target_roles: Union[List[str], str],
    severity: str,
    title: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
    station_code: str = "NDLS",
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """Universal event bus helper: records notification in SQLite and dispatches outbound alerts."""
    database = db or get_db()
    roles_list = [target_roles] if isinstance(target_roles, str) else list(target_roles)
    target_role_str = ",".join(roles_list)
    payload_json = json.dumps(payload or {})
    now_iso = datetime.now(timezone.utc).isoformat()
    sev_normalized = severity.lower()
    if sev_normalized not in ("info", "warning", "critical"):
        sev_normalized = "info"

    with database.transaction() as cur:
        cur.execute(
            """
            INSERT INTO notifications (
                event_type, target_role, severity, title, message, payload_json,
                state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'sent', ?);
            """,
            (
                event_type,
                target_role_str,
                sev_normalized,
                title,
                message,
                payload_json,
                now_iso,
            ),
        )
        notif_id = cur.lastrowid

    # If warning or critical, trigger field dispatcher
    dispatcher = get_dispatcher(database)
    legacy_severity = "HIGH" if sev_normalized == "critical" else ("MEDIUM" if sev_normalized == "warning" else "LOW")
    alert_event = AlertEvent(
        severity=legacy_severity,
        event_type=event_type,
        title=title,
        body=message,
        station_code=station_code,
        roles=roles_list,
        ack_id=f"NOTIF-{notif_id}",
        metadata=payload or {},
        created_at=now_iso,
    )

    dispatch_res = dispatcher.dispatch(alert_event)

    return {
        "notification_id": notif_id,
        "event_type": event_type,
        "severity": sev_normalized,
        "title": title,
        "state": "sent",
        "created_at": now_iso,
        "dispatch_summary": dispatch_res,
    }


def acknowledge_notification(
    notif_id: int,
    user_id: str,
    channel: str = "in_app",
    notes: Optional[str] = None,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """Marks a notification as acknowledged and records an entry in notification_ack."""
    database = db or get_db()
    now_iso = datetime.now(timezone.utc).isoformat()

    with database.transaction() as cur:
        cur.execute("SELECT * FROM notifications WHERE id = ?;", (notif_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Notification with id {notif_id} not found.")

        cur.execute(
            """
            UPDATE notifications
            SET state = 'acked', acked_at = ?, acked_by = ?
            WHERE id = ?;
            """,
            (now_iso, user_id, notif_id),
        )

        cur.execute(
            """
            INSERT INTO notification_ack (notif_id, user_id, channel, ack_ts, notes)
            VALUES (?, ?, ?, ?, ?);
            """,
            (notif_id, user_id, channel, now_iso, notes or ""),
        )

    return {
        "notification_id": notif_id,
        "state": "acked",
        "acked_at": now_iso,
        "acked_by": user_id,
    }


def escalate_unacked_notifications(
    max_age_minutes: int = 5,
    db: Optional[Database] = None,
) -> List[Dict[str, Any]]:
    """Escalates unacknowledged critical and warning notifications older than max_age_minutes to supervisors."""
    database = db or get_db()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    escalated_items = []

    with database.transaction() as cur:
        cur.execute(
            """
            SELECT id, event_type, target_role, severity, title, message, payload_json, created_at
            FROM notifications
            WHERE state = 'sent' AND severity IN ('critical', 'warning') AND escalated_at IS NULL;
            """
        )
        rows = cur.fetchall()

        for r in rows:
            created_dt = datetime.fromisoformat(r["created_at"])
            age_min = (now - created_dt).total_seconds() / 60.0
            if age_min >= max_age_minutes:
                cur.execute(
                    """
                    UPDATE notifications
                    SET state = 'escalated', escalated_at = ?
                    WHERE id = ?;
                    """,
                    (now_iso, r["id"]),
                )
                escalated_items.append({
                    "id": r["id"],
                    "event_type": r["event_type"],
                    "severity": r["severity"],
                    "title": f"[ESCALATED] {r['title']}",
                    "message": f"Unacknowledged after {int(age_min)} minutes. Escalated to Station Master / Supervisor. Original alert: {r['message']}",
                    "created_at": r["created_at"],
                    "escalated_at": now_iso,
                })

    # Outbound alert to Station Master and Admin
    dispatcher = get_dispatcher(database)
    for esc in escalated_items:
        esc_event = AlertEvent(
            severity="HIGH",
            event_type=f"ESCALATION_{esc['event_type']}",
            title=esc["title"],
            body=esc["message"],
            station_code="NDLS",
            roles=["station_master", "admin"],
            ack_id=f"ESC-{esc['id']}",
            metadata={"original_notif_id": esc["id"]},
            created_at=now_iso,
        )
        dispatcher.dispatch(esc_event, bypass_rate_limit=True)

    return escalated_items
