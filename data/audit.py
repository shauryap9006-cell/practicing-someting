"""RailTwin-X Cryptographic Append-Only Audit Trail (Module I3).

Provides tamper-evident, SHA-256 hash-chained audit logging for all station mutations,
guaranteeing provable provenance and non-repudiation across all operating system actions.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from data.db import Database, get_db

GENESIS_HASH = "0" * 64


def compute_audit_hash(
    prev_hash: str,
    ts: str,
    actor_id: str,
    actor_role: str,
    action: str,
    table_name: str,
    record_id: str,
    before_state: Optional[str],
    after_state: Optional[str],
) -> str:
    """Computes deterministic SHA-256 hash linking the current audit entry to the previous row."""
    payload = (
        f"{prev_hash}|{ts}|{actor_id}|{actor_role}|{action}|{table_name}|{record_id}|"
        f"{before_state or ''}|{after_state or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_last_audit_hash(cursor: sqlite3.Cursor) -> str:
    """Retrieves the latest row_hash in the audit_log table, or GENESIS_HASH if empty."""
    cursor.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    if row and row[0]:
        return str(row[0])
    return GENESIS_HASH


def record_audit(
    db_or_cursor: Union[Database, sqlite3.Cursor, None],
    actor_id: str,
    actor_role: str,
    action: str,
    table_name: str,
    record_id: Union[str, int],
    before_state: Optional[Union[Dict[str, Any], str]] = None,
    after_state: Optional[Union[Dict[str, Any], str]] = None,
) -> Dict[str, Any]:
    """Records an append-only, SHA-256 chained audit log entry.
    
    Accepts either an active sqlite3.Cursor (inside an existing transaction) or a Database instance.
    """
    ts = datetime.now(timezone.utc).isoformat()
    record_id_str = str(record_id)
    
    before_str = json.dumps(before_state, sort_keys=True) if isinstance(before_state, dict) else before_state
    after_str = json.dumps(after_state, sort_keys=True) if isinstance(after_state, dict) else after_state

    def _execute_audit(cur: sqlite3.Cursor) -> Dict[str, Any]:
        prev_hash = get_last_audit_hash(cur)
        row_hash = compute_audit_hash(
            prev_hash=prev_hash,
            ts=ts,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            table_name=table_name,
            record_id=record_id_str,
            before_state=before_str,
            after_state=after_str,
        )
        cur.execute(
            """
            INSERT INTO audit_log (
                ts, actor_id, actor_role, action, table_name, record_id,
                before_state, after_state, row_hash, prev_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ts,
                actor_id,
                actor_role,
                action,
                table_name,
                record_id_str,
                before_str,
                after_str,
                row_hash,
                prev_hash,
            ),
        )
        audit_id = cur.lastrowid
        return {
            "id": audit_id,
            "ts": ts,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "table_name": table_name,
            "record_id": record_id_str,
            "before_state": before_str,
            "after_state": after_str,
            "row_hash": row_hash,
            "prev_hash": prev_hash,
        }

    if isinstance(db_or_cursor, sqlite3.Cursor):
        return _execute_audit(db_or_cursor)
    
    db = db_or_cursor if isinstance(db_or_cursor, Database) else get_db()
    with db.transaction() as cur:
        return _execute_audit(cur)


def verify_audit_chain_integrity(db: Optional[Database] = None) -> Tuple[bool, int, Optional[str]]:
    """Verifies the complete SHA-256 cryptographic chain of the audit_log table.
    
    Returns:
        (is_valid, total_records_checked, error_message_if_invalid)
    """
    database = db or get_db()
    with database.transaction() as cur:
        cur.execute(
            """
            SELECT id, ts, actor_id, actor_role, action, table_name, record_id,
                   before_state, after_state, row_hash, prev_hash
            FROM audit_log
            ORDER BY id ASC;
            """
        )
        rows = cur.fetchall()

    if not rows:
        return True, 0, None

    expected_prev = GENESIS_HASH
    for idx, row in enumerate(rows):
        (
            rec_id,
            ts,
            actor_id,
            actor_role,
            action,
            table_name,
            record_id,
            before_state,
            after_state,
            row_hash,
            prev_hash,
        ) = row

        if prev_hash != expected_prev:
            return (
                False,
                idx,
                f"Broken chain at record ID {rec_id}: prev_hash '{prev_hash}' does not match expected '{expected_prev}'",
            )

        calculated_hash = compute_audit_hash(
            prev_hash=prev_hash,
            ts=ts,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            table_name=table_name,
            record_id=str(record_id),
            before_state=before_state,
            after_state=after_state,
        )

        if row_hash != calculated_hash:
            return (
                False,
                idx,
                f"Corrupted record at ID {rec_id}: stored row_hash '{row_hash}' does not match calculated '{calculated_hash}'",
            )

        expected_prev = row_hash

    return True, len(rows), None
