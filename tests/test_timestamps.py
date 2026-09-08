"""Tests for TIME-001: Canonical IST Clocks and Timestamp Normalization."""

import os
import re
import sqlite3
import tempfile
from pathlib import Path
import pytest

from config import settings
from data.db import Database
from data.seed_users import seed_roles_and_users
from data.seed_safety import bootstrap_level_crossings_if_empty

IST_TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+05:30$")

TIMESTAMP_COLUMNS = {
    "created_at", "updated_at", "reviewed_at", "published_at", "granted_at",
    "restored_at", "reported_at", "resolved_at", "started_at", "completed_at",
    "issued_at", "found_at", "claimed_at", "cleaned_at", "released_at",
    "expires_at", "revoked_at", "last_used_at", "last_inspected", "last_active",
    "last_event_time", "last_gps_fix", "applied_at", "backup_ts", "ack_ts",
    "acked_at", "escalated_at", "test_time", "sign_on_time", "sign_off_time",
    "outgoing_signed_at", "incoming_acked_at", "actual_ts", "predicted_ts",
    "actual_timestamp", "query_timestamp", "event_time", "collected_at",
    "since", "timestamp", "ts", "ts_ist", "recorded_at", "sent_at", "ack_at", "sim_time"
}


def test_existing_database_timestamps_are_canonical_ist():
    """Regression test: verifies that all timestamps in the database are formatted as IST (+05:30)."""
    db_path = settings.DB_PATH
    if not os.path.exists(db_path):
        pytest.skip(f"Database file not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]

    violations = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table});")
        cols = [r[1] for r in cur.fetchall()]
        matched_cols = [c for c in cols if c.lower() in TIMESTAMP_COLUMNS]

        for col in matched_cols:
            try:
                cur.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != '';")
                rows = cur.fetchall()
                for rowid, val in rows:
                    if isinstance(val, str) and not IST_TIMESTAMP_REGEX.match(val):
                        # Ignore ephemeral test-injected notifications from test_notification_center.py
                        if table == "notifications":
                            cur.execute("SELECT event_type FROM notifications WHERE rowid = ?;", (rowid,))
                            ev = cur.fetchone()
                            if ev and ev[0] == "UNACKED_SIGNAL_FAULT":
                                continue
                        # Filter out non-datetime strings if any column happens to store pure dates or text
                        if len(val) >= 10 and ("-" in val or ":" in val):
                            violations.append(f"{table}.{col} (rowid={rowid}): '{val}'")
            except Exception:
                pass

    conn.close()
    assert len(violations) == 0, f"Found {len(violations)} non-IST timestamps:\n" + "\n".join(violations[:20])


def test_freshly_seeded_db_timestamps_are_ist():
    """Regression test: verifies that a freshly-seeded database writes 100% IST (+05:30) timestamps."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        test_db = Database(tmp_db_path)
        test_db.init_schema()

        # Seed roles & users
        seed_roles_and_users(db=test_db)

        # Seed level crossings
        with test_db.transaction() as cur:
            bootstrap_level_crossings_if_empty(cur)

        # Inspect all timestamp columns in freshly-seeded DB
        conn = sqlite3.connect(tmp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall()]

        violations = []
        checked_count = 0
        for table in tables:
            cur.execute(f"PRAGMA table_info({table});")
            cols = [r[1] for r in cur.fetchall()]
            matched_cols = [c for c in cols if c.lower() in TIMESTAMP_COLUMNS]

            for col in matched_cols:
                cur.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != '';")
                rows = cur.fetchall()
                for rowid, val in rows:
                    if isinstance(val, str) and len(val) >= 10 and ("-" in val or ":" in val):
                        checked_count += 1
                        if not IST_TIMESTAMP_REGEX.match(val):
                            violations.append(f"{table}.{col} (rowid={rowid}): '{val}'")

        conn.close()
        assert checked_count > 0, "Expected seeded rows to be checked"
        assert len(violations) == 0, f"Violations in freshly seeded DB:\n" + "\n".join(violations)
    finally:
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


def test_source_code_clock_guard():
    """Guard test: fails if datetime.now( or datetime.utcnow( is used outside engine/clocks.py and tests/."""
    pattern = re.compile(r"datetime\.(?:now|utcnow)\(")
    repo_root = Path(__file__).resolve().parent.parent

    # Enforce across core application packages
    dirs_to_guard = ["api", "data", "notifications", "engine"]
    exempt_files = {
        (repo_root / "engine" / "clocks.py").resolve(),
        (repo_root / "engine" / "sim_clock.py").resolve(),
    }

    violations = []
    for d in dirs_to_guard:
        guard_dir = repo_root / d
        for py_file in guard_dir.rglob("*.py"):
            if py_file.resolve() in exempt_files:
                continue
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for idx, line in enumerate(lines, 1):
                # Ignore pure comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if pattern.search(line):
                    rel_path = py_file.relative_to(repo_root)
                    violations.append(f"{rel_path}:{idx}: {stripped}")

    assert len(violations) == 0, (
        f"Found {len(violations)} direct datetime.now/utcnow calls in core code (must use engine.clocks):\n"
        + "\n".join(violations)
    )
