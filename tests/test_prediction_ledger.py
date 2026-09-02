"""Unit tests for Tamper-Evident Prediction Ledger & Public Scoreboard (Proposal 2)."""

import hashlib
import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db
from engine.prediction_ledger import PredictionLedger, GENESIS_HASH


@pytest.fixture
def client():
    return TestClient(app)


def test_prediction_ledger_records_hash_chain():
    """Ledger must record sequential predictions and form an unbroken SHA-256 hash chain."""
    db = get_db()
    ledger = PredictionLedger(db)
    
    # Record 3 sequential predictions
    h1 = ledger.record_prediction_receipt("12004", "CNB", 5.0, 10.0, 20.0, "2026-08-29T10:00:00")
    h2 = ledger.record_prediction_receipt("12424", "PRYJ", 0.0, 5.0, 12.0, "2026-08-29T10:01:00")
    h3 = ledger.record_prediction_receipt("12301", "DDU", 15.0, 25.0, 45.0, "2026-08-29T10:02:00")
    
    assert len(h1) == 64
    assert len(h2) == 64
    assert len(h3) == 64
    assert h1 != h2 != h3
    
    # Verify chain integrity
    is_valid, count, broken_id = ledger.verify_chain_integrity()
    assert is_valid is True
    assert count >= 3
    assert broken_id is None


def test_prediction_ledger_grades_actual_arrival():
    """Grading actual arrivals must compute absolute error, in-band indicator, and Winkler score."""
    db = get_db()
    ledger = PredictionLedger(db)
    
    # Record test prediction
    test_train = f"TEST-{abs(hash('train')) % 9000 + 1000}"
    h = ledger.record_prediction_receipt(test_train, "CNB", 10.0, 20.0, 30.0, "2026-08-29T12:00:00")
    
    # Grade with in-band actual arrival (delay = 22.0 min)
    graded = ledger.grade_actual_arrival(test_train, "CNB", 22.0, "2026-08-29T12:30:00")
    assert graded >= 1
    
    scoreboard = ledger.get_calibration_scoreboard()
    assert scoreboard["total_served_predictions"] >= 1
    assert scoreboard["verified_arrivals_count"] >= 1
    assert 0.0 <= scoreboard["empirical_80pct_coverage"] <= 100.0
    assert scoreboard["chain_integrity_verified"] is True


def test_ledger_detects_tampering():
    """Manually tampering with a stored block must be detected by verify_chain_integrity."""
    db = get_db()
    ledger = PredictionLedger(db)
    
    # Ensure at least one entry exists
    ledger.record_prediction_receipt("12034", "CNB", 5.0, 10.0, 15.0)
    
    with db.transaction() as cur:
        cur.execute("SELECT id, p50_delay FROM eta_prediction_ledger ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        assert row is not None
        target_id = row["id"]
        orig_p50 = float(row["p50_delay"])
        
        # Tamper with recorded delay
        cur.execute("UPDATE eta_prediction_ledger SET p50_delay = p50_delay + 999.0 WHERE id = ?;", (target_id,))
        
    # Chain verification must now fail
    is_valid, _, broken_id = ledger.verify_chain_integrity()
    assert is_valid is False
    assert broken_id == target_id
    
    # Revert tampering
    with db.transaction() as cur:
        cur.execute("UPDATE eta_prediction_ledger SET p50_delay = ? WHERE id = ?;", (orig_p50, target_id))
    
    # Verify restored
    is_valid_restored, _, _ = ledger.verify_chain_integrity()
    assert is_valid_restored is True


def test_ledger_api_endpoints(client):
    """GET /v1/ledger/scoreboard and /v1/ledger/verify must return valid JSON responses."""
    r_board = client.get("/v1/ledger/scoreboard")
    assert r_board.status_code == 200
    b_data = r_board.json()
    assert b_data["status"] == "OK"
    assert "scoreboard" in b_data
    assert "empirical_80pct_coverage" in b_data["scoreboard"]
    assert "chain_tip_hash" in b_data["scoreboard"]
    
    r_ver = client.get("/v1/ledger/verify")
    assert r_ver.status_code == 200
    v_data = r_ver.json()
    assert v_data["status"] == "OK"
    assert v_data["chain_integrity_verified"] is True
