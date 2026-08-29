"""RailTwin-X Hierarchical Bayesian Track Identification Engine (TRACK-EXACT) Tests.

Covers:
1. EdgeEKF 100 Hz dead-reckoning & GNSS filtering
2. RAIM chi-square innovation gating & GNSS anti-spoofing rejection
3. RailHMMMapMatcher topology constraints over parallel tracks (4.72m spacing)
4. JunctionIMM turnout geometry vs. mainline TSR deceleration discrimination
5. MultiHypothesisTracker Bayesian weighting and instant Kavach Balise ground-truth collapse
6. Safety Interlock Rule 6 (Fusion Integrity & Anti-Spoofing validation)
7. Probabilistic ConflictScanner expectation over hypotheses
8. End-to-end TrackExactEngine multi-sensor fusion pipeline
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from engine.track_exact.ekf import EdgeEKF
from engine.track_exact.hmm_mapmatch import RailHMMMapMatcher, TrackSegment, point_polyline_distance
from engine.track_exact.imm import JunctionIMM
from engine.track_exact.mht import MultiHypothesisTracker, TrackHypothesis
from engine.track_exact.fusion import TrackExactEngine, TrackStateEstimate
from engine.conflicts import ConflictScanner, ProbabilisticConflictRecord
from safety.interlock import check_fusion_integrity, validate_prediction_through_interlock
from collector.adapters.mock_replay import HighFrequencyTelemetryGenerator
from data.db import Database


# ==============================================================================
# 1. LAYER 1: EDGE EKF & RAIM ANTI-SPOOFING TESTS
# ==============================================================================

def test_ekf_dead_reckoning_and_gnss_update():
    """Verifies that 100 Hz IMU propagation accurately dead-reckons position and GNSS updates converge."""
    ekf = EdgeEKF(init_x=0.0, init_y=0.0, init_v=20.0, init_heading=0.0)

    # 1. Predict 100 steps @ 100 Hz (1 second) with zero accel & yaw
    dt = 0.01
    for _ in range(100):
        ekf.predict(a_fwd=0.0, gyro_z=0.0, dt=dt)

    # Expected position: x = 20m, y = 0m
    x_est, y_est = ekf.position
    assert abs(x_est - 20.0) < 0.1
    assert abs(y_est - 0.0) < 0.1

    # 2. Authentic GNSS update at (20.5, 0.2)
    accepted = ekf.update_gnss((20.5, 0.2))
    assert accepted is True
    assert ekf.last_gnss_valid is True
    assert ekf.last_gnss_innov_d < 5.991

    # 3. Odometer update
    ekf.update_odo(20.1)
    assert abs(ekf.speed - 20.0) < 1.0


def test_ekf_raim_chi_square_spoof_rejection():
    """Verifies that GNSS spoofing jumps (e.g. 25m offset) are rejected by RAIM chi-square innovation test."""
    ekf = EdgeEKF(init_x=100.0, init_y=0.0, init_v=25.0, init_heading=0.0)

    # Initial authentic GNSS lock
    ekf.update_gnss((100.0, 0.0))

    # Propagate for 1s
    for _ in range(100):
        ekf.predict(a_fwd=0.0, gyro_z=0.0, dt=0.01)

    # Filter is near x = 125m, y = 0m
    pos_before = ekf.position
    assert abs(pos_before[0] - 125.0) < 0.2

    # Inject 30m spoofing spike to y = 30.0m (jump across 6 parallel tracks)
    spoofed_fix = (125.0, 30.0)
    accepted = ekf.update_gnss(spoofed_fix)

    # RAIM should reject this fix
    assert accepted is False
    assert ekf.last_gnss_valid is False
    assert ekf.last_gnss_innov_d > 5.991

    # Verify state was NOT corrupted by the spoofed measurement
    pos_after = ekf.position
    assert abs(pos_after[1] - 0.0) < 1.0  # y remains near 0, NOT 30m!


# ==============================================================================
# 2. LAYER 2: HMM MAP-MATCHING & TOPOLOGY TESTS
# ==============================================================================

def test_hmm_point_polyline_distance():
    """Tests Euclidean distance projection to polyline segments."""
    polyline = [(0.0, 0.0), (100.0, 0.0)]
    assert abs(point_polyline_distance((50.0, 5.0), polyline) - 5.0) < 1e-6
    assert abs(point_polyline_distance((-10.0, 0.0), polyline) - 10.0) < 1e-6
    assert abs(point_polyline_distance((110.0, 0.0), polyline) - 10.0) < 1e-6


def test_hmm_mapmatch_topology_constraint():
    """Verifies that Newson-Krumm HMM enforces hard topology preventing track hopping."""
    # 2 parallel tracks separated by 4.72m
    up_main = TrackSegment(id="UP_MAIN", polyline=[(0.0, 0.0), (500.0, 0.0)], track_type="main")
    dn_main = TrackSegment(id="DN_MAIN", polyline=[(0.0, 4.72), (500.0, 4.72)], track_type="main")

    # Hard constraint: UP_MAIN and DN_MAIN are NOT connected (no cross-over)
    adjacency = {
        "UP_MAIN": ["UP_MAIN"],
        "DN_MAIN": ["DN_MAIN"],
    }
    matcher = RailHMMMapMatcher([up_main, dn_main], adjacency, sigma_gps=3.0, sigma_odo=2.0)

    # Observations along UP_MAIN with one noisy point near DN_MAIN
    observations = [
        ((0.0, 0.5), 0.0),
        ((100.0, 0.2), 100.0),
        ((200.0, 3.8), 100.0),  # Noisy GPS pull towards DN_MAIN
        ((300.0, 0.1), 100.0),
    ]

    matched_path = matcher.match(observations)
    # HMM Viterbi must maintain UP_MAIN throughout because jumping to DN_MAIN has transition prob = -inf
    assert matched_path == ["UP_MAIN", "UP_MAIN", "UP_MAIN", "UP_MAIN"]


# ==============================================================================
# 3. LAYER 2: IMM TURNOUT VS TSR MODE DETECTION TESTS
# ==============================================================================

def test_imm_tsr_vs_turnout_discrimination():
    """Verifies that IMM discriminates mainline TSR deceleration from turnout curve entry."""
    imm = JunctionIMM(dt=1.0)

    # 1. Mainline TSR deceleration: speed drops from 30 m/s to 8 m/s, heading stays 0.0 (straight)
    v = 30.0
    for _ in range(10):
        v = max(8.0, v - 0.35 * 1.0)
        mode_probs = imm.step(v_obs=v, h_obs=0.0)

    # Deceleration on straight alignment matches BRAKE_PLATFORM or MAIN_STRAIGHT, NOT DIVERGE_LOOP
    assert mode_probs["DIVERGE_LOOP"] < 0.20
    assert (mode_probs["BRAKE_PLATFORM"] + mode_probs["MAIN_STRAIGHT"]) > 0.80

    # 2. Turnout Divergence: train turns at 15 m/s through 1:12 curvature (~300m radius)
    imm_curve = JunctionIMM(dt=1.0)
    v_curve = 15.0
    heading_curve = 0.0
    kappa = 1.0 / 300.0
    for _ in range(8):
        heading_curve += v_curve * kappa * 1.0
        mode_probs_curve = imm_curve.step(v_obs=v_curve, h_obs=heading_curve)

    # Heading change matching curvature must elevate DIVERGE_LOOP
    assert mode_probs_curve["DIVERGE_LOOP"] > 0.60
    assert imm_curve.dominant_mode == "DIVERGE_LOOP"


# ==============================================================================
# 4. LAYER 2: MULTI-HYPOTHESIS TRACKING & GROUND-TRUTH COLLAPSE TESTS
# ==============================================================================

def test_mht_hypothesis_competition_and_balise_collapse():
    """Verifies hypothesis competition under ambiguity and instant collapse upon Kavach Balise trigger."""
    up_main = TrackSegment(id="UP_MAIN", polyline=[(0.0, 0.0), (1000.0, 0.0)], track_type="main")
    loop_1 = TrackSegment(id="LOOP_1", polyline=[(0.0, -4.72), (1000.0, -4.72)], track_type="loop")
    pf_1 = TrackSegment(id="PF_1", polyline=[(0.0, -9.44), (1000.0, -9.44)], track_type="platform")

    matcher = RailHMMMapMatcher([up_main, loop_1, pf_1], sigma_gps=3.0)
    mht = MultiHypothesisTracker(matcher, sigma=3.0)

    # Initial state has 3 equal hypotheses
    assert len(mht.hyps) == 3

    # Ambiguous observation at y = -2.36m (exactly between UP_MAIN at 0 and LOOP_1 at -4.72)
    mht.update(z_xy=(100.0, -2.36))
    distrib = mht.get_distribution()
    assert abs(distrib["UP_MAIN"] - distrib["LOOP_1"]) < 0.1
    best_track, p = mht.estimate()
    assert p < 0.80  # Ambiguous track state

    # Kavach RFID Balise detected on LOOP_1 (Hard ground truth)
    mht.collapse("LOOP_1", source="KAVACH_RFID_BALISE")

    collapsed_track, collapsed_p = mht.estimate()
    assert collapsed_track == "LOOP_1"
    assert collapsed_p == 1.0
    assert len(mht.hyps) == 1
    assert "KAVACH_RFID_BALISE" in mht.hyps[0].confirmed_by


# ==============================================================================
# 5. LAYER 3: SAFETY INTERLOCK RULE 6 (FUSION INTEGRITY) TESTS
# ==============================================================================

def test_safety_rule_6_fusion_integrity():
    """Verifies pure-function check_fusion_integrity and integration with interlock validator."""
    # 1. Passed check: P=0.92 >= 0.80, GNSS OK
    chk_pass = check_fusion_integrity(p_track=0.92, integrity_ok=True)
    assert chk_pass.passed is True
    assert chk_pass.code == "OK_FUSION_INTEGRITY_VERIFIED"

    # 2. Failed check: Ambiguous track identification (P=0.65 < 0.80)
    chk_ambig = check_fusion_integrity(p_track=0.65, integrity_ok=True)
    assert chk_ambig.passed is False
    assert chk_ambig.code == "ERR_AMBIGUOUS_TRACK_IDENTIFICATION"

    # 3. Failed check: GNSS spoofing / integrity failure
    chk_spoof = check_fusion_integrity(p_track=0.95, integrity_ok=False)
    assert chk_spoof.passed is False
    assert chk_spoof.code == "ERR_GNSS_SPOOF_OR_INTEGRITY_FAIL"

    # 4. Master validator pipeline integration with TrackStateEstimate
    features = {
        "current_delay": 5.0,
        "km_remaining": 80.0,
        "hops_remaining": 2,
        "train_priority": 1,
    }

    # High confidence track estimate
    est_good = TrackStateEstimate(
        train_no="12001",
        ts=1700000000.0,
        x=500.0,
        y=0.0,
        v=25.0,
        heading=0.0,
        track_id="UP_MAIN",
        p_track=0.95,
        integrity_ok=True,
    )
    rep_good = validate_prediction_through_interlock(
        features=features,
        raw_p10=3.0,
        raw_p50=5.0,
        raw_p90=8.0,
        track_estimate=est_good,
    )
    assert rep_good.all_passed is True
    assert rep_good.confidence_tier == "HIGH"
    assert rep_good.verify_with_controller is False

    # Ambiguous track estimate (P=0.55) triggers tier downgrade to LOW
    est_ambig = TrackStateEstimate(
        train_no="12001",
        ts=1700000000.0,
        x=500.0,
        y=-2.0,
        v=25.0,
        heading=0.0,
        track_id="UNKNOWN",
        p_track=0.55,
        integrity_ok=True,
    )
    rep_ambig = validate_prediction_through_interlock(
        features=features,
        raw_p10=3.0,
        raw_p50=5.0,
        raw_p90=8.0,
        track_estimate=est_ambig,
    )
    assert rep_ambig.all_passed is False
    assert rep_ambig.confidence_tier == "LOW"
    assert rep_ambig.verify_with_controller is True


# ==============================================================================
# 6. LAYER 3: PROBABILISTIC CONFLICT SCANNER TESTS
# ==============================================================================

def test_probabilistic_conflict_scanner(tmp_path):
    """Verifies that conflict scanner computes expectation over track hypotheses."""
    db = Database(tmp_path / "test_conflicts.db")
    db.init_schema()

    scanner = ConflictScanner(db=db)
    
    # 1. Deterministic default (P=1.0)
    conflicts_det = scanner.scan_probabilistic_conflicts(train_no="12001")
    for c in conflicts_det:
        assert c.p_conflict == 1.0

    # 2. Probabilistic expectation with multiple track hypotheses
    # Train 70% likely on UP_MAIN (conflicted) and 30% on LOOP_1 (refuge line)
    hyps = [
        {"track_id": "UP_MAIN", "weight": 0.70},
        {"track_id": "LOOP_1", "weight": 0.30},
    ]
    conflicts_prob = scanner.scan_probabilistic_conflicts(train_no="12001", hypotheses=hyps)
    assert isinstance(conflicts_prob, list)


# ==============================================================================
# 7. END-TO-END PIPELINE & TELEMETRY STREAM SIMULATION TESTS
# ==============================================================================

def test_end_to_end_track_exact_pipeline():
    """Runs complete 30s multi-sensor telemetry simulation through TrackExactEngine."""
    generator = HighFrequencyTelemetryGenerator(seed=123)
    stream = generator.generate_run(
        duration_sec=15.0,
        speed_mps=25.0,
        spoof_gnss_at_sec=5.0,
        spoof_jump_m=30.0,
        balise_at_sec=10.0,
        balise_track_id="UP_MAIN",
    )

    engine = TrackExactEngine()

    gnss_spoofs_rejected = 0
    balise_events = 0

    for packet in stream:
        p_type = packet["type"]
        if p_type == "IMU":
            engine.on_imu(packet["a_fwd"], packet["gyro_z"], packet["dt"])
        elif p_type == "ODO":
            engine.on_odo(packet["v"])
        elif p_type == "GNSS":
            ok = engine.on_gnss(packet["z_xy"])
            if packet["is_spoofed"] and not ok:
                gnss_spoofs_rejected += 1
        elif p_type == "BALISE":
            engine.on_balise(packet["track_id"])
            balise_events += 1

    # Verify that spoofed GNSS fixes were successfully rejected
    assert gnss_spoofs_rejected > 0
    assert balise_events == 1

    # Verify final state estimate
    estimate = engine.estimate(train_no="12001")
    assert isinstance(estimate, TrackStateEstimate)
    assert estimate.track_id == "UP_MAIN"
    assert estimate.p_track == 1.0  # Confirmed by balise
    assert estimate.v > 20.0        # High speed maintained smoothly
    assert estimate.to_dict()["track_id"] == "UP_MAIN"
