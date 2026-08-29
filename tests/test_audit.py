"""RailTwin-X Cryptographic Audit Trail Test Suite (Module I3).

Verifies tamper-evident append-only SHA-256 hash chaining, query filters,
and cryptographic integrity validation against adversarial mutations.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.main import app
from data.audit import (
    GENESIS_HASH,
    compute_audit_hash,
    record_audit,
    verify_audit_chain_integrity,
)
from data.db import Database, get_db
from data.seed_users import seed_roles_and_users

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_clean_audit_log():
    """Seeds users and cleans audit log before and after each audit test for deterministic chain verification."""
    db = get_db()
    seed_roles_and_users(db)
    with db.transaction() as cur:
        cur.execute("DELETE FROM audit_log;")
    yield
    with db.transaction() as cur:
        cur.execute("DELETE FROM audit_log;")


def test_audit_hash_computation_deterministic():
    """Verifies that SHA-256 hash computation is completely deterministic."""
    h1 = compute_audit_hash(
        prev_hash=GENESIS_HASH,
        ts="2026-08-28T12:00:00Z",
        actor_id="usr-sm-01",
        actor_role="station_master",
        action="PLATFORM_REASSIGN",
        table_name="platform_assignments",
        record_id="101",
        before_state='{"platform": 1}',
        after_state='{"platform": 2}',
    )
    h2 = compute_audit_hash(
        prev_hash=GENESIS_HASH,
        ts="2026-08-28T12:00:00Z",
        actor_id="usr-sm-01",
        actor_role="station_master",
        action="PLATFORM_REASSIGN",
        table_name="platform_assignments",
        record_id="101",
        before_state='{"platform": 1}',
        after_state='{"platform": 2}',
    )
    assert h1 == h2
    assert len(h1) == 64


def test_audit_record_and_chain_verification():
    """Verifies that multiple sequential audit entries form a valid cryptographic chain."""
    db = get_db()
    rec1 = record_audit(
        db_or_cursor=db,
        actor_id="usr-sm-01",
        actor_role="station_master",
        action="TSR_CREATED",
        table_name="speed_restrictions",
        record_id=1,
        after_state={"speed_limit": 30},
    )
    rec2 = record_audit(
        db_or_cursor=db,
        actor_id="usr-admin-01",
        actor_role="admin",
        action="CONFIG_UPDATED",
        table_name="system_config",
        record_id=2,
        after_state={"mode": "LIVE"},
    )

    assert rec2["prev_hash"] == rec1["row_hash"]

    is_valid, count, err = verify_audit_chain_integrity(db)
    assert is_valid is True
    assert count >= 2
    assert err is None


def test_audit_adversarial_tampering_detection():
    """Adversarial test: artificially tamper with an audit record in SQLite and verify detection."""
    db = get_db()
    record_audit(
        db_or_cursor=db,
        actor_id="usr-sm-01",
        actor_role="station_master",
        action="INITIAL_ACTION",
        table_name="platform_assignments",
        record_id=1,
        after_state={"platform": 1},
    )

    with db.transaction() as cur:
        cur.execute("SELECT id FROM audit_log ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        assert row is not None
        rec_id = row["id"]
        cur.execute(
            "UPDATE audit_log SET action = 'MALICIOUS_TAMPER' WHERE id = ?;",
            (rec_id,),
        )

    is_valid, count, err = verify_audit_chain_integrity(db)
    assert is_valid is False
    assert "Corrupted record" in str(err) or "Broken chain" in str(err)


def test_api_audit_verify_integrity():
    """Verifies that the /api/audit/verify-integrity endpoint returns status."""
    db = get_db()
    record_audit(
        db_or_cursor=db,
        actor_id="usr-sm-01",
        actor_role="station_master",
        action="VALID_ACTION",
        table_name="platform_assignments",
        record_id=1,
    )
    admin_token = create_access_token({"sub": "admin", "role_id": "admin"})
    response = client.get(
        "/api/audit/verify-integrity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["total_records_checked"] >= 1
