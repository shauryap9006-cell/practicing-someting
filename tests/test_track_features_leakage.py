"""Unit and Leakage Tests for Track Context Features (Phase G1).

Verifies point-in-time integrity: future station events or position reports
never leak into snapshot track-context features.
"""

import datetime
import pytest
from data.db import Database
from engine.track_graph import TrackGraph
from ml.snapshots import SnapshotGenerator
from ml.features import FEATURE_NAMES, TrainFeatureVector


@pytest.fixture
def memory_db(tmp_path):
    test_db_path = tmp_path / "leakage_test.db"
    db = Database(test_db_path)
    db.init_schema()
    with db.transaction() as cur:
        # Seed test stations
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_A', 'Alpha', 28.0, 77.0, 4, 1)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_B', 'Bravo', 28.3, 77.4, 3, 0)")
        cur.execute("INSERT INTO stations (code, name, lat, lon, platforms, is_junction) VALUES ('STN_C', 'Charlie', 28.6, 77.8, 4, 1)")

        # Seed test sections: STN_A <-> STN_B (single line), STN_B <-> STN_C (double line)
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('STN_A', 'STN_B', 25.0, 1, 100)")
        cur.execute("INSERT INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph) VALUES ('STN_B', 'STN_C', 35.0, 0, 120)")

        # Seed train 101, 102, 103 with valid class
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('101', 'Express 1', 'superfast', 2)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('102', 'Express 2', 'superfast', 2)")
        cur.execute("INSERT INTO trains (train_no, name, class, priority) VALUES ('103', 'Opposing 3', 'superfast', 2)")

        # Routes: 101 and 102 go A -> B -> C. 103 goes C -> B -> A (opposing)
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('101', 1, 'STN_A', '08:00', '08:05', 5, 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('101', 2, 'STN_B', '08:30', '08:35', 5, 25.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('101', 3, 'STN_C', '09:15', '09:20', 5, 60.0)")

        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('102', 1, 'STN_A', '08:15', '08:20', 5, 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('102', 2, 'STN_B', '08:45', '08:50', 5, 25.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('102', 3, 'STN_C', '09:30', '09:35', 5, 60.0)")

        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('103', 1, 'STN_C', '08:00', '08:05', 5, 0.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('103', 2, 'STN_B', '08:40', '08:45', 5, 35.0)")
        cur.execute("INSERT INTO route_stations (train_no, seq, station_code, sched_arr, sched_dep, halt_min, distance_km) VALUES ('103', 3, 'STN_A', '09:10', '09:15', 5, 60.0)")

        # Events: Train 102 passed STN_A at 08:20 (delay +5m)
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('102', '2026-08-25', 1, 'STN_A', '08:15', '08:20', '08:20', '08:25', 5, 5, '2026-08-25T08:25:00+05:30')")
        # FUTURE EVENT of Train 102 (collected at 09:00, 35 mins after query time 08:25)
        cur.execute("INSERT INTO station_events (train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep, delay_arr_min, delay_dep_min, collected_at) VALUES ('102', '2026-08-25', 2, 'STN_B', '08:45', '08:58', '08:50', '09:02', 13, 12, '2026-08-25T09:02:00+05:30')")

    return db


def test_track_context_temporal_leakage_isolation(memory_db):
    """Proves that future station_events collected after query_time do NOT leak into features."""
    tg = TrackGraph(memory_db)

    # Query snapshot for Train 101 at STN_A at 08:25:00
    feats_asof = tg.compute_track_context_features(
        train_no="101",
        current_seq=1,
        target_seq=3,
        run_date_str="2026-08-25",
        query_time_iso="2026-08-25T08:25:00+05:30",
        current_delay=0.0,
    )

    # At 08:25, train 102 is recorded ONLY at seq 1 (STN_A), NOT at seq 2 (STN_B with +13m delay)
    assert feats_asof["trains_ahead_30k"] == 0.0, "Train 102 is at same station (seq 1), not ahead in distance."
    assert feats_asof["sum_delay_trains_ahead_30k"] == 0.0, "Future delay (+13m) must not leak."

    # When query time advances past 09:05:00, the event at seq 2 becomes visible
    feats_later = tg.compute_track_context_features(
        train_no="101",
        current_seq=1,
        target_seq=3,
        run_date_str="2026-08-25",
        query_time_iso="2026-08-25T09:05:00+05:30",
        current_delay=0.0,
    )

    assert feats_later["trains_ahead_30k"] == 1.0, "Train 102 at STN_B (25km ahead) is now point-in-time visible."
    assert feats_later["sum_delay_trains_ahead_30k"] == 13.0, "Delay at STN_B (+13m) is legitimately known at 09:05."


def test_feature_vector_schema_completeness(memory_db):
    """Verifies all 23 features in TrainFeatureVector are populated and valid."""
    sg = SnapshotGenerator(memory_db)
    sg.compute_train_period_statistics("2026-08-25")

    vec = sg.extract_features_at_snapshot(
        train_no="101",
        current_seq=1,
        target_seq=2,
        run_date_str="2026-08-25",
        current_delay=2.0,
        prev_delay=0.0,
        query_time_iso="2026-08-25T08:20:00+05:30",
    )

    d = vec.to_dict()
    assert len(FEATURE_NAMES) == 25
    for f in FEATURE_NAMES:
        assert f in d, f"Missing feature {f}"
        assert d[f] is not None
        assert not isinstance(d[f], (list, dict))
