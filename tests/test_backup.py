"""RailTwin-X Backup & Disaster Recovery Test Suite (Module I5).

Verifies WAL-safe online backups, rolling retention enforcement, SHA-256 integrity,
and automated restore into scratch SQLite databases.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.db import Database, get_db
from scripts.backup_db import (
    create_database_backup,
    enforce_retention_policy,
    verify_backup_file,
)

client = TestClient(app)


def test_backup_creation_and_checksum():
    """Verifies that an online backup creates a valid SQLite database with matching tables."""
    db = get_db()
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = create_database_backup(db=db, backup_dir=tmp_dir, tag="test")
        backup_path = Path(res["path"])
        assert backup_path.exists()
        assert res["size_bytes"] > 0
        assert len(res["checksum_sha256"]) == 64
        assert res["status"] == "SUCCESS"

        # Verify tables in backup file
        backup_db = Database(backup_path)
        counts = backup_db.table_counts()
        assert counts.get("stations", 0) > 0


def test_backup_restore_verification():
    """Verifies that verify_backup_file restores into scratch database and passes integrity check."""
    db = get_db()
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = create_database_backup(db=db, backup_dir=tmp_dir, tag="test_verify")
        v_res = verify_backup_file(res["path"])
        assert v_res["is_valid"] is True
        assert v_res["integrity_check"] == "ok"


def test_backup_retention_policy():
    """Verifies that older backups are pruned when exceeding retention limit."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create 10 dummy daily backups
        for i in range(10):
            p = tmp_path / f"railtwin_backup_daily_202608{i+10:02d}_120000.db"
            p.write_text("dummy")

        removed = enforce_retention_policy(tmp_path, max_daily=7)
        assert len(removed) == 3
        remaining = list(tmp_path.glob("railtwin_backup_daily_*.db"))
        assert len(remaining) == 7


def test_api_backup_list_and_create():
    """Verifies admin backup API endpoints."""
    admin_token = create_access_token({"sub": "admin", "role_id": "admin"})
    
    # Create backup via API
    create_resp = client.post(
        "/api/admin/backups/create",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "SUCCESS"

    # List backups via API
    list_resp = client.get(
        "/api/admin/backups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    backups = list_resp.json()
    assert len(backups) >= 1
