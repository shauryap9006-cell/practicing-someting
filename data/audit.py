"""RailTwin-X Cryptographic Append-Only Audit Trail (Module I3).

Provides tamper-evident, SHA-256 hash-chained audit logging for all station mutations,
guaranteeing provable provenance and non-repudiation across all operating system actions.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from typing import Any, Dict, Optional, Tuple, Union

from data.db import Database, get_db
from engine.clocks import get_clock

GENESIS_HASH = "0" * 64
_AUDIT_LOCK = threading.Lock()


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
    record_id: Union[str, int, None] = None,
    before_state: Optional[Union[Dict[str, Any], str]] = None,
    after_state: Optional[Union[Dict[str, Any], str]] = None,
) -> Dict[str, Any]:
    """Records an append-only, SHA-256 chained audit log entry with concurrency safety.

    Accepts either an active sqlite3.Cursor (inside an existing transaction) or a Database instance.
    """
    clock = get_clock()
    record_id_str = str(record_id) if record_id is not None else ""

    before_str = (
        json.dumps(before_state, sort_keys=True) if isinstance(before_state, dict) else before_state
    )
    after_str = (
        json.dumps(after_state, sort_keys=True) if isinstance(after_state, dict) else after_state
    )

    def _execute_audit(cur: sqlite3.Cursor) -> Dict[str, Any]:
        prev_hash = get_last_audit_hash(cur)
        ts = clock.now_iso()
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
        with _AUDIT_LOCK:
            return _execute_audit(db_or_cursor)

    db = db_or_cursor if isinstance(db_or_cursor, Database) else get_db()
    max_attempts = 5
    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            with _AUDIT_LOCK:
                with db.transaction() as cur:
                    cur.execute("BEGIN IMMEDIATE")
                    return _execute_audit(cur)
        except sqlite3.IntegrityError as err:
            last_error = err
        except sqlite3.OperationalError as err:
            # Contended writers under WAL surface as 'database is locked'; retry briefly.
            if "locked" not in str(err).lower() and "busy" not in str(err).lower():
                raise
            last_error = err
        time.sleep(0.01 * (2**attempt))
    assert last_error is not None
    raise last_error


def append_audit_entry(*args, **kwargs) -> Dict[str, Any]:
    """Alias for record_audit supporting flexible argument signatures."""
    if args and (isinstance(args[0], (Database, sqlite3.Cursor)) or args[0] is None):
        return record_audit(*args, **kwargs)

    actor_id = kwargs.pop("actor_id", args[0] if len(args) > 0 else "system")
    actor_role = kwargs.pop("actor_role", args[1] if len(args) > 1 else "service")
    action = kwargs.pop("action", args[2] if len(args) > 2 else "MUTATION")
    table_name = kwargs.pop("table_name", args[3] if len(args) > 3 else "audit")
    record_id = kwargs.pop("record_id", args[4] if len(args) > 4 else "0")
    before_state = kwargs.pop("before_state", args[5] if len(args) > 5 else None)
    after_state = kwargs.pop("after_state", args[6] if len(args) > 6 else None)
    db = kwargs.pop("db", kwargs.pop("db_or_cursor", None))

    return record_audit(
        db_or_cursor=db,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        table_name=table_name,
        record_id=record_id,
        before_state=before_state,
        after_state=after_state,
    )


def verify_audit_log(db: Optional[Database] = None) -> Tuple[bool, int, int]:
    """Reads chain, computes SHA-256 for each block, returns (is_valid, fork_count, total_blocks)."""
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
        return True, 0, 0

    seen_prevs = set()
    fork_count = 0
    all_valid = True
    expected_prev = GENESIS_HASH

    for row in rows:
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

        if prev_hash in seen_prevs:
            fork_count += 1
        seen_prevs.add(prev_hash)

        if prev_hash != expected_prev:
            all_valid = False

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
            all_valid = False

        expected_prev = row_hash

    is_valid = all_valid and (fork_count == 0)
    return is_valid, fork_count, len(rows)


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
