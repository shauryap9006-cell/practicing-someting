"""Tests for DPDP Act 2023 PII Retention and Purge Policy (PRIV-001)."""

import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from config import Settings, settings
from data.db import Database
from scripts.purge_expired_pii import hash_pnr, purge_expired_pii

KOLKATA = ZoneInfo("Asia/Kolkata")


def test_pii_retention_days_setting():
    """Verifies default setting and environment variable override support."""
    assert settings.PII_RETENTION_DAYS == 90
    custom = Settings(PII_RETENTION_DAYS=180)
    assert custom.PII_RETENTION_DAYS == 180


def test_hash_pnr_pseudonymization():
    """Verifies SHA-256 prefix hashing for PNR numbers."""
    assert hash_pnr(None) is None
    assert hash_pnr("") is None
    h1 = hash_pnr("1234567890")
    assert h1 is not None
    assert h1.startswith("SHA256:")
    assert len(h1) == 7 + 16  # 'SHA256:' + 16 hex chars
    # Deterministic
    assert hash_pnr("1234567890") == h1
    # Idempotent (does not re-hash already hashed string)
    assert hash_pnr(h1) == h1


@pytest.fixture
def test_db_with_backdated_pii(tmp_path: Path) -> tuple[Database, datetime.datetime]:
    """Creates a temporary database with both expired (backdated) and fresh PII records."""
    db_file = tmp_path / "privacy_test.db"
    db = Database(db_file)
    db.init_schema()

    now = datetime.datetime(2026, 9, 8, 12, 0, 0, tzinfo=KOLKATA)
    cutoff_100d = (now - datetime.timedelta(days=100)).isoformat()
    cutoff_120d = (now - datetime.timedelta(days=120)).isoformat()
    cutoff_10d = (now - datetime.timedelta(days=10)).isoformat()

    conn = db.get_connection()
    try:
        cur = conn.cursor()

        # Insert stations and staff for foreign key integrity
        cur.execute(
            """
            INSERT OR IGNORE INTO stations (code, name, lat, lon, platforms) VALUES
            ('NDLS', 'New Delhi', 28.6143, 77.2144, 16),
            ('CNB', 'Kanpur Central', 26.4547, 80.3507, 10);
            """
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO staff (staff_id, name, role, phone, station_code, pin_hash, on_duty) VALUES
            ('STF_001', 'Rajesh Sharma', 'station_master', '+919876500001', 'NDLS', 'hash1', 1),
            ('STF_002', 'Sunil Yadav', 'station_master', '+919876500002', 'NDLS', 'hash2', 1),
            ('STF_003', 'Anil Verma', 'controller', '+919876500003', 'CNB', 'hash3', 1);
            """
        )

        # 1. Expired delay certificates (100d and 120d old)
        cur.execute(
            """
            INSERT INTO delay_certificates (
                cert_no, pnr_no, train_no, train_name, station_code,
                scheduled_arr, actual_arr, delay_min, reason,
                issued_to_name, issued_by, issued_at, qr_token
            ) VALUES
            ('CERT-EXP-001', '1111111111', '12034', 'Express', 'NDLS', '10:00', '10:45', 45, 'Signal Hold', 'Rohan Sharma', 'SM_NDLS', ?, 'QR-EXP-001'),
            ('CERT-EXP-002', '2222222222', '12034', 'Express', 'CNB', '12:00', '13:10', 70, 'Track Work', 'Pooja Verma', 'SM_CNB', ?, 'QR-EXP-002');
            """,
            (cutoff_100d, cutoff_120d),
        )

        # Fresh delay certificate (10d old)
        cur.execute(
            """
            INSERT INTO delay_certificates (
                cert_no, pnr_no, train_no, train_name, station_code,
                scheduled_arr, actual_arr, delay_min, reason,
                issued_to_name, issued_by, issued_at, qr_token
            ) VALUES
            ('CERT-FRESH-001', '3333333333', '12034', 'Express', 'NDLS', '10:00', '10:30', 30, 'Speed Limit', 'Vikram Malhotra', 'SM_NDLS', ?, 'QR-FRESH-001');
            """,
            (cutoff_10d,),
        )

        # 2. Expired notification log entries (100d and 120d old)
        cur.execute(
            """
            INSERT INTO notification_log (staff_id, event_type, severity, channel, status, payload, sent_at)
            VALUES
            ('STF_001', 'ALERT', 'CRITICAL', 'whatsapp', 'sent', 'SMS to +919876543210: Platform blocked', ?),
            ('STF_002', 'ALERT', 'HIGH', 'sms', 'sent', 'SMS to +919876543211: Signal warning', ?);
            """,
            (cutoff_100d, cutoff_120d),
        )

        # Fresh notification log entry (10d old)
        cur.execute(
            """
            INSERT INTO notification_log (staff_id, event_type, severity, channel, status, payload, sent_at)
            VALUES
            ('STF_003', 'ALERT', 'LOW', 'in_app', 'sent', 'Notification for Section Controller', ?);
            """,
            (cutoff_10d,),
        )

        # 3. Expired claimant in lost_and_found (100d old)
        cur.execute(
            """
            INSERT INTO lost_and_found (
                item_type, description, found_location, station_code, found_at,
                found_by_staff, custody_location, status, claimant_name, claimant_id_proof, claimant_phone, claimed_at
            ) VALUES
            ('WALLET_CASH', 'Black leather wallet', 'PF 1 Bench', 'NDLS', ?, 'STF_001', 'Station Safe', 'CLAIMED', 'Amit Patel', 'Aadhaar 1234-5678-9012', '+919988776655', ?);
            """,
            (cutoff_120d, cutoff_100d),
        )

        # Fresh claimant in lost_and_found (10d old)
        cur.execute(
            """
            INSERT INTO lost_and_found (
                item_type, description, found_location, station_code, found_at,
                found_by_staff, custody_location, status, claimant_name, claimant_id_proof, claimant_phone, claimed_at
            ) VALUES
            ('ELECTRONICS', 'Mobile Phone', 'Waiting Hall', 'NDLS', ?, 'STF_002', 'Station Safe', 'CLAIMED', 'Suresh Raina', 'Voter ID ABC1234567', '+919876500000', ?);
            """,
            (cutoff_120d, cutoff_10d),
        )

        conn.commit()
    finally:
        conn.close()

    return db, now


def test_dry_run_identifies_expired_rows_without_modifications(test_db_with_backdated_pii):
    """Verifies that dry-run mode detects exact expired counts without modifying any data."""
    db, now = test_db_with_backdated_pii

    # Run purge in dry-run mode (apply=False)
    stats = purge_expired_pii(db=db, days=90, apply=False, now_dt=now)

    assert stats["dry_run"] is True
    assert stats["apply"] is False
    assert stats["delay_certificates"] == 2
    assert stats["notification_log"] == 2
    assert stats["lost_and_found"] == 1
    assert stats["total_affected"] == 5

    # Confirm database content was NOT modified
    conn = db.get_connection()
    try:
        cur = conn.cursor()

        # Check delay certificates still hold original PII
        cur.execute(
            "SELECT cert_no, issued_to_name, pnr_no FROM delay_certificates ORDER BY cert_no;"
        )
        certs = cur.fetchall()
        assert len(certs) == 3
        assert certs[0]["issued_to_name"] == "Rohan Sharma"
        assert certs[0]["pnr_no"] == "1111111111"
        assert certs[1]["issued_to_name"] == "Pooja Verma"
        assert certs[1]["pnr_no"] == "2222222222"
        assert certs[2]["issued_to_name"] == "Vikram Malhotra"
        assert certs[2]["pnr_no"] == "3333333333"

        # Check notification log still has 3 rows
        cur.execute("SELECT COUNT(*) FROM notification_log;")
        assert cur.fetchone()[0] == 3

        # Check lost and found still has original claimant PII
        cur.execute(
            "SELECT claimant_name, claimant_id_proof FROM lost_and_found WHERE status='CLAIMED' ORDER BY id;"
        )
        claims = cur.fetchall()
        assert claims[0]["claimant_name"] == "Amit Patel"
        assert claims[1]["claimant_name"] == "Suresh Raina"
    finally:
        conn.close()


def test_apply_redacts_expired_and_preserves_fresh(test_db_with_backdated_pii):
    """Verifies that --apply redacts/purges expired data while leaving fresh rows untouched."""
    db, now = test_db_with_backdated_pii

    # Run purge with apply=True
    stats = purge_expired_pii(db=db, days=90, apply=True, now_dt=now)

    assert stats["dry_run"] is False
    assert stats["apply"] is True
    assert stats["delay_certificates"] == 2
    assert stats["notification_log"] == 2
    assert stats["lost_and_found"] == 1
    assert stats["total_affected"] == 5

    conn = db.get_connection()
    try:
        cur = conn.cursor()

        # 1. Delay Certificates verification
        cur.execute(
            "SELECT cert_no, issued_to_name, pnr_no FROM delay_certificates ORDER BY cert_no;"
        )
        certs = cur.fetchall()
        # CERT-EXP-001 (expired) -> REDACTED and hashed PNR
        assert certs[0]["cert_no"] == "CERT-EXP-001"
        assert certs[0]["issued_to_name"] == "REDACTED"
        assert certs[0]["pnr_no"].startswith("SHA256:")
        assert certs[0]["pnr_no"] != "1111111111"

        # CERT-EXP-002 (expired) -> REDACTED and hashed PNR
        assert certs[1]["cert_no"] == "CERT-EXP-002"
        assert certs[1]["issued_to_name"] == "REDACTED"
        assert certs[1]["pnr_no"].startswith("SHA256:")
        assert certs[1]["pnr_no"] != "2222222222"

        # CERT-FRESH-001 (fresh, 10d old) -> completely untouched
        assert certs[2]["cert_no"] == "CERT-FRESH-001"
        assert certs[2]["issued_to_name"] == "Vikram Malhotra"
        assert certs[2]["pnr_no"] == "3333333333"

        # 2. Notification log verification
        cur.execute("SELECT staff_id FROM notification_log;")
        remaining_logs = cur.fetchall()
        assert len(remaining_logs) == 1
        assert remaining_logs[0]["staff_id"] == "STF_003"  # fresh row remains

        # 3. Lost & Found verification
        cur.execute(
            "SELECT claimant_name, claimant_id_proof, claimant_phone FROM lost_and_found ORDER BY id;"
        )
        claims = cur.fetchall()
        # First row (expired)
        assert claims[0]["claimant_name"] == "REDACTED"
        assert claims[0]["claimant_id_proof"] == "REDACTED"
        assert claims[0]["claimant_phone"] == "REDACTED"

        # Second row (fresh)
        assert claims[1]["claimant_name"] == "Suresh Raina"
        assert claims[1]["claimant_id_proof"] == "Voter ID ABC1234567"
        assert claims[1]["claimant_phone"] == "+919876500000"
    finally:
        conn.close()


def test_purge_idempotency(test_db_with_backdated_pii):
    """Verifies that running purge twice has zero side-effects and reports 0 rows affected on subsequent runs."""
    db, now = test_db_with_backdated_pii

    # First run: applies changes
    stats1 = purge_expired_pii(db=db, days=90, apply=True, now_dt=now)
    assert stats1["total_affected"] == 5

    # Second run: should report 0 records affected
    stats2 = purge_expired_pii(db=db, days=90, apply=True, now_dt=now)
    assert stats2["delay_certificates"] == 0
    assert stats2["notification_log"] == 0
    assert stats2["lost_and_found"] == 0
    assert stats2["total_affected"] == 0

    # Third run (dry-run): should also find 0 expired unredacted records
    stats3 = purge_expired_pii(db=db, days=90, apply=False, now_dt=now)
    assert stats3["total_affected"] == 0


def test_cli_execution(test_db_with_backdated_pii, monkeypatch, capsys):
    """Verifies that the CLI executes cleanly in dry-run and apply modes."""
    import sys

    from scripts.purge_expired_pii import main

    db, _ = test_db_with_backdated_pii

    # Run CLI in dry-run mode
    monkeypatch.setattr(
        sys, "argv", ["purge_expired_pii.py", "--db-path", str(db.db_path), "--days", "90"]
    )
    ret = main()
    assert ret == 0
    captured = capsys.readouterr().out
    assert "DRY-RUN (no changes made)" in captured

    # Run CLI in apply mode
    monkeypatch.setattr(
        sys,
        "argv",
        ["purge_expired_pii.py", "--db-path", str(db.db_path), "--days", "90", "--apply"],
    )
    ret = main()
    assert ret == 0
    captured = capsys.readouterr().out
    assert "APPLIED (DB updated)" in captured
