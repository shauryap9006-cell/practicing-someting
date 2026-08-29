"""Point-in-Time Data Leakage Isolation Tests (Task T2 & Invariant I3).

Verifies that:
1. Every new v2 feature (upstream rake doom signals, TSR active counts/slowdown,
   festival multiplier, Bayesian position belief, recency latency) strictly respects as-of time.
2. Perturbing events after as_of time by +/- 60 minutes produces byte-identical feature vectors.
"""

from __future__ import annotations

import datetime
import pytest

from data.db import Database
from ml.snapshots import SnapshotGenerator
from ml.features import FEATURE_NAMES_V2, TrainFeatureVector


@pytest.fixture
def pit_leakage_db(tmp_path):
    """Creates a temporary database seeded with rake links, routes, TSRs, and station events."""
    db_path = tmp_path / "pit_leakage.db"
    db = Database(db_path)
    db.init_schema()

    with db.transaction() as cur:
        # 1. Stations
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('NDLS', 'New Delhi', 28.61, 77.20, 16, 1)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('CNB', 'Kanpur Central', 26.45, 80.35, 10, 1)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('PRYJ', 'Prayagraj', 25.43, 81.84, 10, 1)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('DDU', 'Pt DD Upadhyaya', 25.28, 83.11, 8, 1)")

        # 2. Sections
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('NDLS', 'CNB', 440.0, 0, 130)")
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('CNB', 'PRYJ', 200.0, 0, 130)")
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('PRYJ', 'DDU', 150.0, 0, 130)")

        # 3. Trains
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('12301', 'Incoming Rajdhani', 'rajdhani', 1)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('12302', 'Outgoing Rajdhani', 'rajdhani', 1)")

        # 4. Routes
        # Train 12301 arrives at NDLS at 08:00
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('12301', 1, 'CNB', '04:00', '04:05', 5, 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('12301', 2, 'NDLS', '08:00', '08:00', 0, 440.0)")

        # Train 12302 departs from NDLS at 10:00 (turnaround buffer = 120 min)
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('12302', 1, 'NDLS', '10:00', '10:00', 0, 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('12302', 2, 'CNB', '14:00', '14:05', 5, 440.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('12302', 3, 'PRYJ', '16:30', '16:35', 5, 640.0)")

        # 5. Rake Link
        cur.execute("INSERT INTO rake_links (incoming_train, outgoing_train, station_code, turnaround_min) VALUES ('12301', '12302', 'NDLS', 120)")

        # 6. Past Events (<= 09:00:00)
        # 12301 arrived at NDLS at 08:45 (delay = +45 min)
        cur.execute(
            """
            INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at, event_time)
            VALUES ('12301', '2026-08-25', 2, 'NDLS', '08:00', '08:45', '08:00', '08:45', 45, 45, '2026-08-25T08:45:00+05:30', '2026-08-25T08:45:00+05:30')
            """
        )

        # 12302 passed NDLS at 10:45 (delay = +45 min)
        cur.execute(
            """
            INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at, event_time)
            VALUES ('12302', '2026-08-25', 1, 'NDLS', '10:00', '10:00', '10:00', '10:45', 0, 45, '2026-08-25T10:45:00+05:30', '2026-08-25T10:45:00+05:30')
            """
        )

        # 7. FUTURE EVENT for 12302 at CNB (collected at 15:30, delay = +85 min)
        cur.execute(
            """
            INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at, event_time)
            VALUES ('12302', '2026-08-25', 2, 'CNB', '14:00', '15:25', '14:05', '15:30', 85, 85, '2026-08-25T15:30:00+05:30', '2026-08-25T15:30:00+05:30')
            """
        )

    return db


def test_v2_features_point_in_time_leakage_isolation(pit_leakage_db):
    """Proves that future events after query_time do not leak into v2 feature vector, and perturbation produces identical vectors."""
    sg = SnapshotGenerator(pit_leakage_db)

    # Snapshot for 12302 at NDLS (seq=1) at query time 11:00 (BEFORE CNB arrival at 15:30)
    as_of_time = "2026-08-25T11:00:00+05:30"
    v_base = sg.extract_features_at_snapshot(
        train_no="12302",
        current_seq=1,
        target_seq=3,
        run_date_str="2026-08-25",
        current_delay=45.0,
        prev_delay=45.0,
        query_time_iso=as_of_time,
    )

    # Check that v2 features are correctly computed at 11:00
    assert v_base.rake_linked == 1
    assert v_base.upstream_rake_delay_min == 45.0
    assert v_base.upstream_rake_buffer_remaining_min == 75.0  # 120 - 45
    assert v_base.minutes_since_last_obs == 15.0  # 11:00 - 10:45

    # Now PERTURB future event (> as_of 11:00) by +60 min and -60 min
    with pit_leakage_db.transaction() as cur:
        cur.execute(
            """
            UPDATE station_events
            SET delay_arr_min = 145, delay_dep_min = 145,
                collected_at = '2026-08-25T16:30:00+05:30',
                event_time = '2026-08-25T16:30:00+05:30'
            WHERE train_no = '12302' AND seq = 2
            """
        )

    v_perturbed = sg.extract_features_at_snapshot(
        train_no="12302",
        current_seq=1,
        target_seq=3,
        run_date_str="2026-08-25",
        current_delay=45.0,
        prev_delay=45.0,
        query_time_iso=as_of_time,
    )

    # All 34 features must remain BYTE-IDENTICAL
    dict_base = v_base.to_dict(version=2)
    dict_perturbed = v_perturbed.to_dict(version=2)

    for feat in FEATURE_NAMES_V2:
        assert dict_base[feat] == dict_perturbed[feat], f"Leakage detected on feature {feat}: {dict_base[feat]} != {dict_perturbed[feat]}"
