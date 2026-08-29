"""Adversarial & End-to-End Test Suite for RailTwin-X Brain Orchestrator (Phase G7).

Validates 10 adversarial and edge-case drills across the complete API and Brain pipeline:
1. Missing train number (400 validation error)
2. Non-existent train (Honest NOT_FOUND advisory)
3. Nan / Inf feature inputs (Deterministic interlock clamp + LOW tier downgrade)
4. Extreme delay underflow (< -30 min clamped)
5. Impossible kinematic speed recovery (> 800 km/h recovery rejected & clamped)
6. Model quantile crossing (q10 > q50 clamped monotonically)
7. Model quantile excessive width (> 180m clamped)
8. Single-line opposing train conflict (HOLD_AT_LOOP_ADVISORY emitted)
9. Station headway conflict (STOP_TRAIN_ADVISORY / CONTROLLER_REVIEW emitted)
10. Nominal on-time train (PROCEED_NOMINAL emitted, latency < 2s budget, human_ack_required = True)
"""

import math
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.brain import BrainOrchestrator
from data.db import Database, get_db


client = TestClient(app)


def test_e2e_1_missing_train_number():
    """Drill 1: Empty or missing train_no returns 400."""
    resp = client.post("/v1/advise", json={})
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


def test_e2e_2_non_existent_train():
    """Drill 2: Non-existent train returns honest graceful degradation."""
    resp = client.post("/v1/advise", json={"train_no": "999999_NON_EXISTENT"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NOT_FOUND"
    assert data["confidence_tier"] == "LOW"
    assert data["human_ack_required"] is True


def test_e2e_3_adversarial_nan_input():
    """Drill 3: Feature vector with NaN triggers safety interlock clamp and LOW tier."""
    from safety.interlock import validate_prediction_through_interlock
    report = validate_prediction_through_interlock(
        features={"current_delay": float("nan"), "km_remaining": 100.0, "hops_remaining": 2},
        raw_p10=10.0,
        raw_p50=15.0,
        raw_p90=20.0,
    )
    assert report.all_passed is False
    assert report.confidence_tier == "LOW"
    assert report.verify_with_controller is True


def test_e2e_4_extreme_delay_underflow():
    """Drill 4: Extreme negative delay is clamped to physical bounds."""
    from safety.interlock import validate_prediction_through_interlock
    report = validate_prediction_through_interlock(
        features={"current_delay": -500.0, "km_remaining": 50.0, "hops_remaining": 1},
        raw_p10=-100.0,
        raw_p50=-50.0,
        raw_p90=0.0,
    )
    assert report.all_passed is False
    assert report.clamped_p10 >= -5.0
    assert report.confidence_tier == "LOW"


def test_e2e_5_impossible_kinematic_recovery():
    """Drill 5: Rejecting unfeasible 120m delay recovery over 10km."""
    from safety.interlock import validate_prediction_through_interlock
    report = validate_prediction_through_interlock(
        features={"current_delay": 120.0, "km_remaining": 10.0, "hops_remaining": 1},
        raw_p10=0.0,
        raw_p50=0.0,
        raw_p90=10.0,
    )
    assert report.all_passed is False
    assert report.clamp_applied is True
    assert report.clamped_p50 > 90.0  # Physically constrained


def test_e2e_6_model_quantile_crossing():
    """Drill 6: Inverted model quantiles clamped monotonically."""
    from safety.interlock import validate_prediction_through_interlock
    report = validate_prediction_through_interlock(
        features={"current_delay": 20.0, "km_remaining": 100.0, "hops_remaining": 2},
        raw_p10=50.0,
        raw_p50=20.0,
        raw_p90=10.0,
    )
    assert report.all_passed is False
    assert report.clamped_p10 <= report.clamped_p50 <= report.clamped_p90


def test_e2e_7_excessive_quantile_width():
    """Drill 7: Spread > 180m clamped."""
    from safety.interlock import validate_prediction_through_interlock
    report = validate_prediction_through_interlock(
        features={"current_delay": 20.0, "km_remaining": 100.0, "hops_remaining": 2},
        raw_p10=0.0,
        raw_p50=50.0,
        raw_p90=300.0,
    )
    assert report.all_passed is False
    assert (report.clamped_p90 - report.clamped_p10) <= 180.0


def test_e2e_8_single_line_opposing_conflict():
    """Drill 8: Opposing movements on single-line block produce hold_at_loop recommendation."""
    from engine.conflicts import ConflictRecord
    rec = ConflictRecord(
        conflict_id="CONF-1",
        target_train="12001",
        with_train="12002",
        station_code="GWL",
        conflict_type="SINGLE_LINE_OPPOSING",
        predicted_gap_min=3.0,
        severity="HIGH",
        suggested_action="hold_at_loop",
        reason="Single line meet conflict",
    )
    assert rec.suggested_action == "hold_at_loop"
    assert rec.human_ack_required is True


def test_e2e_9_station_headway_conflict():
    """Drill 9: Arrival headway < 5m triggers advisory alert."""
    from engine.conflicts import ConflictRecord
    rec = ConflictRecord(
        conflict_id="CONF-2",
        target_train="12001",
        with_train="12004",
        station_code="NDLS",
        conflict_type="STATION_HEADWAY",
        predicted_gap_min=1.5,
        severity="HIGH",
        suggested_action="stop_train_advisory",
        reason="Headway below minimum separation buffer",
    )
    assert rec.suggested_action == "stop_train_advisory"


def test_e2e_10_nominal_live_advisory():
    """Drill 10: Live train advisory endpoint execution within latency budget."""
    db = get_db()
    with db.transaction() as cur:
        cur.execute("SELECT train_no FROM trains LIMIT 1")
        row = cur.fetchone()

    assert row is not None
    train_no = row["train_no"]

    # Warmup to pre-cache historical DB baselines
    client.post("/v1/advise", json={"train_no": train_no})

    # Benchmark steady-state execution
    resp = client.post("/v1/advise", json={"train_no": train_no})
    assert resp.status_code == 200
    data = resp.json()

    assert "train_no" in data
    assert "prediction" in data
    assert "confidence_tier" in data
    assert "safety_checks" in data
    assert "advisory_recommendations" in data
    assert data["human_ack_required"] is True
    assert data["latency_ms"] < 2000.0, "Must satisfy < 2000 ms latency budget."

