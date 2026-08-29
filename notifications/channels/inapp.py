"""RailTwin-X In-App Notification Channel.

Records all dispatches into the database `notification_log` table
for historical audit trails and station cockpit triage boards.
"""

from __future__ import annotations

import json
from typing import Optional

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from notifications.types import AlertEvent, StaffRecipient


class InAppChannel:
    """Channel adapter recording directly to SQLite notification_log."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def log_dispatch(
        self,
        staff: StaffRecipient,
        event: AlertEvent,
        channel: str,
        status: str,
    ) -> int:
        """Appends a new notification row into notification_log."""
        clock = get_clock()
        sent_at = clock.now_iso()

        payload_dict = {
            "title": event.title,
            "body": event.body,
            "station_code": event.station_code,
            "train_no": event.train_no,
            "ack_id": event.ack_id,
            "metadata": event.metadata,
        }

        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO notification_log (staff_id, event_type, severity, channel, status, payload, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    staff.staff_id,
                    event.event_type,
                    event.severity,
                    channel,
                    status,
                    json.dumps(payload_dict),
                    sent_at,
                ),
            )
            return cur.lastrowid
