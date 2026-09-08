"""Unit tests for Reversible Database Migrations (MIG-001).

Tests:
1. Every forward migration NNN_*.sql has a matching paired NNN_*.down.sql.
2. Fresh DB schema build and migrations application.
3. Round-trip migration test: up to head -> downgrade 2 steps -> re-upgrade to head -> integrity check passes.
4. Downgrade to target version test.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
import pytest

from data.db import Database, MIGRATIONS_DIR


def test_all_migrations_have_paired_downgrade_scripts():
    """Asserts that every forward migration NNN_*.sql has a matching paired NNN_*.down.sql."""
    assert MIGRATIONS_DIR.exists()

    up_files = sorted([f for f in MIGRATIONS_DIR.glob("*.sql") if not f.name.endswith(".down.sql")])
    assert len(up_files) >= 16, f"Expected at least 16 migrations, found {len(up_files)}"

    for up_file in up_files:
        match = re.match(r"^(\d+)_", up_file.name)
        assert match, f"Migration file {up_file.name} does not match NNN_ format"

        stem = up_file.stem
        down_file = up_file.parent / f"{stem}.down.sql"
        assert down_file.exists(), f"Missing paired downgrade script: {down_file.name} for {up_file.name}"
        assert down_file.stat().st_size > 0, f"Downgrade script {down_file.name} is empty"


def test_fresh_db_build_and_downgrade_roundtrip(tmp_path: Path):
    """Verifies fresh DB initialization, 2-step rollback, and re-upgrade to head with PRAGMA integrity_check."""
    db_path = tmp_path / "roundtrip_test.db"
    db = Database(db_path)

    # 1. Fresh DB initialization (schema + all migrations)
    db.init_schema()

    status = db.get_migration_status()
    assert len(status["applied"]) >= 17
    assert len(status["pending"]) == 0

    # Integrity check on fresh schema
    conn = db.get_connection()
    try:
        check = conn.execute("PRAGMA integrity_check;").fetchall()
        assert [tuple(r) for r in check] == [("ok",)]

        # Verify tables/columns from migrations 16 and 17 exist
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users);").fetchall()]
        assert "must_change_password" in user_cols

        indexes = [r[1] for r in conn.execute("SELECT type, name FROM sqlite_master WHERE type='index';").fetchall()]
        assert "idx_audit_prev" in indexes
    finally:
        conn.close()

    # 2. Roll back 2 migrations (v17 and v16)
    rolled = db.downgrade_migrations(steps=2)
    assert len(rolled) == 2
    assert "017_add_must_change_password.down.sql" in rolled[0]
    assert "016_audit_log_index.down.sql" in rolled[1]

    status_after_down = db.get_migration_status()
    assert len(status_after_down["pending"]) == 2
    applied_versions = {r["version"] for r in status_after_down["applied"]}
    assert 17 not in applied_versions
    assert 16 not in applied_versions

    conn = db.get_connection()
    try:
        # Integrity check after downgrade
        check = conn.execute("PRAGMA integrity_check;").fetchall()
        assert [tuple(r) for r in check] == [("ok",)]

        # Verify v17 column dropped and v16 index dropped
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users);").fetchall()]
        assert "must_change_password" not in user_cols

        indexes = [r[1] for r in conn.execute("SELECT type, name FROM sqlite_master WHERE type='index';").fetchall()]
        assert "idx_audit_prev" not in indexes
    finally:
        conn.close()

    # 3. Re-upgrade back to head
    reapplied = db.apply_migrations()
    assert len(reapplied) == 2

    status_after_reup = db.get_migration_status()
    assert len(status_after_reup["pending"]) == 0

    conn = db.get_connection()
    try:
        # Integrity check after re-upgrade
        check = conn.execute("PRAGMA integrity_check;").fetchall()
        assert [tuple(r) for r in check] == [("ok",)]

        # Verify v17 column and v16 index restored
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users);").fetchall()]
        assert "must_change_password" in user_cols

        indexes = [r[1] for r in conn.execute("SELECT type, name FROM sqlite_master WHERE type='index';").fetchall()]
        assert "idx_audit_prev" in indexes
    finally:
        conn.close()


def test_downgrade_to_target_version(tmp_path: Path):
    """Verifies targeted rollback using target_version argument."""
    db_path = tmp_path / "target_version_test.db"
    db = Database(db_path)
    db.init_schema()

    # Downgrade to version 14 (rolling back 17, 16, 15)
    rolled = db.downgrade_migrations(target_version=14)
    assert len(rolled) == 3

    status = db.get_migration_status()
    applied_versions = [r["version"] for r in status["applied"]]
    assert applied_versions[-1] == 14

    conn = db.get_connection()
    try:
        # route_cum_km table (created in v15) should be dropped
        tbl = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='route_cum_km';").fetchone()
        assert tbl is None
    finally:
        conn.close()

    # Re-apply only version 15
    db.apply_migrations(target_version=15)
    conn = db.get_connection()
    try:
        tbl = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='route_cum_km';").fetchone()
        assert tbl is not None
    finally:
        conn.close()

    # Complete upgrade to head
    db.apply_migrations()
    status_final = db.get_migration_status()
    assert len(status_final["pending"]) == 0


def test_fresh_db_rebuild_from_scratch(tmp_path: Path):
    """Verifies that an entirely fresh database builds cleanly through the schema and migration runner."""
    fresh_db_path = tmp_path / "fresh_build.db"
    db = Database(fresh_db_path)
    db.init_schema()

    status = db.get_migration_status()
    assert len(status["applied"]) == 17
    assert len(status["pending"]) == 0

    counts = db.table_counts()
    assert "stations" in counts
    assert "users" in counts

    conn = db.get_connection()
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        assert "route_cum_km" in tables
        assert "auth_sessions" in tables
    finally:
        conn.close()
