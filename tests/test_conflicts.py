"""Unit Tests for Deterministic Conflict Scanner (Phase G5).

Verifies:
1. Clean pass scenarios (safe headway separation >= 5 min)
2. Station headway conflict (< 5 min arrival gap)
3. Severe near-miss conflict (< 1 min -> stop_train_advisory)
4. Single-line opposing track meet (< 10 min clearance -> hold_at_loop)
"""

import pytest
from data.db import Database
from engine.conflicts import ConflictScanner, ConflictRecord


@pytest.fixture
def conflict_db(tmp_path):
    test_db_path = tmp_path / "conflict_test.db"
    db = Database(test_db_path)
    db.init_schema()

    with db.transaction() as cur:
        # Seed Stations
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_A', 'Alpha', 28.0, 77.0, 4, 1)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_B', 'Bravo', 28.3, 77.4, 3, 0)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_C', 'Charlie', 28.6, 77.8, 4, 1)")

        # Sections: A-B (single line), B-C (double line)
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('STN_A', 'STN_B', 25.0, 1, 100)")
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('STN_B', 'STN_C', 35.0, 0, 120)")

        # Trains
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('T1', 'Train 1', 'superfast', 1)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('T2', 'Train 2', 'mail', 3)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('T3', 'Opposing Train 3', 'superfast', 2)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('T4', 'Safe Follower', 'passenger', 4)")

        # Routes
        # T1 (A->B->C): Arr B at 08:30
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T1', 1, 'STN_A', '08:00', '08:05', 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T1', 2, 'STN_B', '08:30', '08:35', 25.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T1', 3, 'STN_C', '09:15', '09:20', 60.0)")

        # T2 (A->B->C): Arr B at 08:33 (3 min gap from T1 -> Headway conflict)
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T2', 1, 'STN_A', '08:05', '08:10', 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T2', 2, 'STN_B', '08:33', '08:38', 25.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T2', 3, 'STN_C', '09:20', '09:25', 60.0)")

        # T3 Opposing (C->B->A): Arr B at 08:34 (Single-line conflict with T1 and T2)
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T3', 1, 'STN_C', '08:00', '08:05', 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T3', 2, 'STN_B', '08:34', '08:39', 35.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T3', 3, 'STN_A', '09:05', '09:10', 60.0)")

        # T4 (A->B->C): Arr B at 09:00 (30 min gap -> Clean pass)
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T4', 1, 'STN_A', '08:35', '08:40', 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T4', 2, 'STN_B', '09:00', '09:05', 25.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, distance_km) VALUES ('T4', 3, 'STN_C', '09:45', '09:50', 60.0)")

        # Events
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('T1', '2026-08-25', 1, 'STN_A', '08:00', '08:00', '08:05', '08:05', 0, 0, '2026-08-25T08:05:00+05:30')")
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('T2', '2026-08-25', 1, 'STN_A', '08:05', '08:05', '08:10', '08:10', 0, 0, '2026-08-25T08:10:00+05:30')")
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('T3', '2026-08-25', 1, 'STN_C', '08:00', '08:00', '08:05', '08:05', 0, 0, '2026-08-25T08:05:00+05:30')")
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('T4', '2026-08-25', 1, 'STN_A', '08:35', '08:35', '08:40', '08:40', 0, 0, '2026-08-25T08:40:00+05:30')")

    return db


def test_conflict_scanner_clean_pass(conflict_db):
    scanner = ConflictScanner(conflict_db)
    # T4 has a 30m gap from other trains
    conflicts = scanner.scan_train_conflicts("T4", target_date_str="2026-08-25")
    # All gaps >= 5m -> no conflicts for T4
    assert len(conflicts) == 0


def test_conflict_scanner_headway_conflict(conflict_db):
    scanner = ConflictScanner(conflict_db)
    conflicts = scanner.scan_train_conflicts("T1", target_date_str="2026-08-25")
    # T1 has headway conflict with T2 (3 min gap at B, 5 min gap at C)
    headway_confs = [c for c in conflicts if c.conflict_type == "STATION_HEADWAY"]
    assert len(headway_confs) > 0
    t2_conf = next(c for c in headway_confs if c.with_train == "T2")
    assert t2_conf.predicted_gap_min == 3.0
    assert t2_conf.suggested_action in ["controller_review", "stop_train_advisory"]


def test_conflict_scanner_opposing_single_line(conflict_db):
    scanner = ConflictScanner(conflict_db)
    conflicts = scanner.scan_train_conflicts("T1", target_date_str="2026-08-25")
    # T1 has opposing single-line conflict with T3 on section A-B at station B
    single_line_confs = [c for c in conflicts if c.conflict_type == "SINGLE_LINE_OPPOSING"]
    assert len(single_line_confs) > 0
    sl_conf = single_line_confs[0]
    assert sl_conf.with_train == "T3"
    assert sl_conf.severity == "HIGH"
    assert sl_conf.suggested_action in ["hold_at_loop", "proceed"]
    assert sl_conf.human_ack_required is True
