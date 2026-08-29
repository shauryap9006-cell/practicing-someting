"""RailTwin-X SQLite WAL-Safe Database Backup & Restore Automation (Module I5).

Executes non-blocking online backups using the SQLite native .backup API, enforces rolling
retention (7 daily, 4 weekly), computes SHA-256 integrity checksums, and performs automated
scratch-database restore verification.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from data.db import Database, get_db

BACKUPS_DIR = Path(__file__).parent.parent / "data" / "backups"


def compute_file_sha256(filepath: Path | str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_database_backup(
    db: Optional[Database] = None,
    backup_dir: Optional[Path | str] = None,
    tag: str = "daily",
) -> Dict[str, Any]:
    """Executes a WAL-safe SQLite native .backup snapshot to disk and logs it in the backups table."""
    database = db or get_db()
    out_dir = Path(backup_dir) if backup_dir else BACKUPS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"railtwin_backup_{tag}_{timestamp_str}.db"
    backup_path = out_dir / backup_filename

    source_conn = database.get_connection()
    try:
        dest_conn = sqlite3.connect(str(backup_path))
        try:
            # Perform native non-blocking SQLite online backup
            source_conn.backup(dest_conn)
            dest_conn.commit()
        finally:
            dest_conn.close()
    finally:
        source_conn.close()

    # Calculate metrics
    size_bytes = backup_path.stat().st_size
    checksum = compute_file_sha256(backup_path)

    # Get row counts in the newly created backup
    dest_db = Database(backup_path)
    row_counts = dest_db.table_counts()
    row_counts_json = json.dumps(row_counts)

    # Record to backups table
    with database.transaction() as cur:
        cur.execute(
            """
            INSERT INTO backups (filename, backup_ts, size_bytes, row_counts_json, status, checksum_sha256)
            VALUES (?, ?, ?, ?, 'SUCCESS', ?);
            """,
            (
                backup_filename,
                now.isoformat(),
                size_bytes,
                row_counts_json,
                checksum,
            ),
        )
        backup_id = cur.lastrowid

    # Enforce rolling retention policy (keep 7 latest daily, 4 weekly)
    enforce_retention_policy(out_dir)

    return {
        "id": backup_id,
        "filename": backup_filename,
        "path": str(backup_path),
        "backup_ts": now.isoformat(),
        "size_bytes": size_bytes,
        "checksum_sha256": checksum,
        "row_counts": row_counts,
        "status": "SUCCESS",
    }


def enforce_retention_policy(backup_dir: Path, max_daily: int = 7, max_weekly: int = 4) -> List[str]:
    """Prunes older backup files exceeding the retention window."""
    removed = []
    daily_backups = sorted(backup_dir.glob("railtwin_backup_daily_*.db"), key=lambda p: p.stat().st_mtime)
    if len(daily_backups) > max_daily:
        to_remove = daily_backups[:-max_daily]
        for p in to_remove:
            p.unlink(missing_ok=True)
            removed.append(p.name)

    weekly_backups = sorted(backup_dir.glob("railtwin_backup_weekly_*.db"), key=lambda p: p.stat().st_mtime)
    if len(weekly_backups) > max_weekly:
        to_remove = weekly_backups[:-max_weekly]
        for p in to_remove:
            p.unlink(missing_ok=True)
            removed.append(p.name)

    return removed


def verify_backup_file(backup_path: Path | str) -> Dict[str, Any]:
    """Restores the backup file into a temporary scratch DB and verifies database integrity and counts."""
    path = Path(backup_path)
    if not path.exists():
        raise FileNotFoundError(f"Backup file not found at: {path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        scratch_path = Path(tmp_dir) / "scratch_restore.db"
        shutil.copy2(path, scratch_path)

        scratch_db = Database(scratch_path)
        conn = scratch_db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            integrity_result = cur.fetchone()[0]
        finally:
            conn.close()

        row_counts = scratch_db.table_counts()
        checksum = compute_file_sha256(path)

    is_valid = integrity_result == "ok" and sum(row_counts.values()) > 0
    return {
        "is_valid": is_valid,
        "integrity_check": integrity_result,
        "checksum_sha256": checksum,
        "row_counts": row_counts,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print("=== RailTwin-X Database Backup & Verification Runner ===")
    res = create_database_backup()
    print(f"Created Backup: {res['filename']} ({res['size_bytes']} bytes)")
    print(f"SHA-256: {res['checksum_sha256']}")
    
    print("Verifying restore in scratch database...")
    v_res = verify_backup_file(res["path"])
    print(f"Integrity Check: {v_res['integrity_check']} (Valid: {v_res['is_valid']})")
