"""Data access and service layer for operational advisories and ACK logging."""

from __future__ import annotations

from typing import Optional
from data.db import Database, get_db
from engine.clocks import get_clock


def record_advisory_ack(
    adv_id: str,
    decision: str,
    dispatcher_id: Optional[str] = None,
    comment: Optional[str] = None,
    channel: str = "web",
    db: Optional[Database] = None,
) -> dict:
    """Helper to record human dispatcher / field staff accept or reject decision."""
    clock = get_clock()
    recorded_at = clock.now_iso()
    if db is None:
        db = get_db()

    with db.transaction() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS advisory_ack_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              adv_id TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('accepted', 'rejected')),
              dispatcher_id TEXT,
              comment TEXT,
              recorded_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            INSERT INTO advisory_ack_log (adv_id, decision, dispatcher_id, comment, recorded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (adv_id, decision, dispatcher_id, comment, recorded_at),
        )
        try:
            cur.execute(
                """
                UPDATE notification_log
                SET ack_at = ?, status = ?
                WHERE id IN (
                    SELECT id FROM notification_log
                    WHERE payload LIKE ? AND ack_at IS NULL
                    ORDER BY id DESC LIMIT 1
                )
                """,
                (recorded_at, f"acked_{decision}", f"%{adv_id}%"),
            )
        except Exception:
            pass

    return {
        "adv_id": adv_id,
        "decision": decision,
        "dispatcher_id": dispatcher_id,
        "comment": comment,
        "recorded_at": recorded_at,
        "channel": channel,
        "status": "ok",
    }
