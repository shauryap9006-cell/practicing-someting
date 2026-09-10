"""Test Suite for WO-10: Domain Features + Schema + Retrain.

Verifies:
- Gate T1: Feature vector contains every new domain feature name:
    loco_class, rake_type, gradient_pct, zone_id, tsr_delay_min,
    signal_aspect, lc_status, sectional_run_time.
- Schema Migration 018: Add columns to trains and sections, and test rollback.
- Data Prep Script: Populates reproducible corridor domain characteristics.
- Gate T3: Snapshot extraction populates domain features without data leakage,
    respecting 2-day temporal embargo.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from data.db import Database, get_db
from ml.features import (
    FEATURE_NAMES,
    FEATURE_NAMES_V1,
    FEATURE_NAMES_V2,
    FEATURE_NAMES_V2_ADDITIONS,
    LOCO_CLASS_ENCODING,
    RAKE_TYPE_ENCODING,
    ZONE_ID_ENCODING,
    SIGNAL_ASPECT_ENCODING,
    TrainFeatureVector,
    get_feature_names,
)
from ml.snapshots import SnapshotGenerator


DOMAIN_FEATURE_NAMES = [
    "loco_class",
    "rake_type",
    "gradient_pct",
    "zone_id",
    "tsr_delay_min",
    "signal_aspect",
    "lc_status",
    "sectional_run_time",
]


def test_t1_feature_vector_contains_every_new_name():
    """GATE T1: Feature vector contains every new domain feature name."""
    v2_names = get_feature_names(version=2)
    for feat in DOMAIN_FEATURE_NAMES:
        assert feat in v2_names, f"Missing domain feature {feat} in FEATURE_NAMES_V2"
        assert feat in FEATURE_NAMES_V2_ADDITIONS, f"Missing {feat} in FEATURE_NAMES_V2_ADDITIONS"

    # Compatibility check: V1 schema length must be preserved for legacy frozen models
    v1_names = get_feature_names(version=1)
    assert len(v1_names) == 25, f"Expected 25 features in V1, got {len(v1_names)}"
    assert len(FEATURE_NAMES) == 25, "Default FEATURE_NAMES alias must remain 25 for compatibility"
    assert len(v2_names) == len(v1_names) + len(FEATURE_NAMES_V2_ADDITIONS)

    # Instantiate feature vector and ensure attributes exist
    sample_kwargs = {
        "current_delay": 5.0,
        "hops_remaining": 3,
        "km_remaining": 120.0,
        "hour_of_day": 14,
        "day_type": 1,
        "train_priority": 1,
        "target_is_junction": 1,
        "target_is_terminus": 0,
        "hist_avg_delay_train_target": 12.0,
        "hist_p90_delay_train_target": 25.0,
        "sched_halt_target_min": 2,
        "sched_congestion_target": 3,
        "fog_flag_target": 0,
        "rain_mm_target": 0.0,
        "active_corridor_trains": 15,
        "delay_velocity": 0.2,
        "chronic_baseline": 8.0,
        "trains_ahead_30k": 1.0,
        "trains_behind_30k": 0.0,
        "opposing_trains_30k": 1.0,
        "min_predicted_headway_next_station": 45.0,
        "sum_delay_trains_ahead_30k": 10.0,
        "section_occupancy_pct": 0.35,
        "rake_incoming_delay": 0.0,
        "crew_duty_pressure": 0.0,
        # v2 fields
        "upstream_rake_delay_min": 0.0,
        "upstream_rake_buffer_remaining_min": 30.0,
        "rake_linked": 0,
        "tsr_active_ahead_count": 1,
        "tsr_max_slowdown_pct": 20.0,
        "festival_load_multiplier": 1.0,
        "position_belief_entropy": 0.0,
        "position_p_mode": 1.0,
        "minutes_since_last_obs": 0.0,
        # domain fields
        "loco_class": 1,
        "rake_type": 1,
        "gradient_pct": 0.15,
        "zone_id": 1,
        "tsr_delay_min": 2.5,
        "signal_aspect": 3,
        "lc_status": 0,
        "sectional_run_time": 18.5,
    }
    vec = TrainFeatureVector(**sample_kwargs)
    for feat in DOMAIN_FEATURE_NAMES:
        assert hasattr(vec, feat), f"TrainFeatureVector missing attribute {feat}"
        val = getattr(vec, feat)
        assert val is not None

    d = vec.to_dict(version=2)
    for feat in DOMAIN_FEATURE_NAMES:
        assert feat in d, f"vec.to_dict(version=2) missing {feat}"


def test_schema_migration_018_and_rollback(tmp_path: Path):
    """Verifies migration 018 schema upgrade and rollback roundtrip."""
    test_db_path = tmp_path / "test_mig.db"
    conn = sqlite3.connect(str(test_db_path))
    cur = conn.cursor()

    # Create baseline tables
    cur.execute("CREATE TABLE trains (train_no TEXT PRIMARY KEY, name TEXT, class TEXT)")
    cur.execute(
        "CREATE TABLE sections (id INTEGER PRIMARY KEY, from_station_code TEXT, to_station_code TEXT)"
    )
    cur.execute("INSERT INTO trains (train_no, name, class) VALUES ('12301', 'Rajdhani', 'rajdhani')")
    cur.execute(
        "INSERT INTO sections (id, from_station_code, to_station_code) VALUES (1, 'NDLS', 'CNB')"
    )
    conn.commit()

    mig_up_path = Path("scripts/migrations/018_domain_features_schema.sql")
    mig_down_path = Path("scripts/migrations/018_domain_features_schema.down.sql")

    assert mig_up_path.exists(), "Migration 018 UP file missing"
    assert mig_down_path.exists(), "Migration 018 DOWN file missing"

    # Apply UP migration
    cur.executescript(mig_up_path.read_text(encoding="utf-8"))
    conn.commit()

    # Verify columns exist
    cur.execute("PRAGMA table_info(trains)")
    train_cols = [r[1] for r in cur.fetchall()]
    assert "loco_class" in train_cols
    assert "rake_type" in train_cols

    cur.execute("PRAGMA table_info(sections)")
    sec_cols = [r[1] for r in cur.fetchall()]
    assert "gradient_pct" in sec_cols
    assert "zone_id" in sec_cols

    # Apply DOWN migration (rollback)
    cur.executescript(mig_down_path.read_text(encoding="utf-8"))
    conn.commit()

    # Verify columns were removed
    cur.execute("PRAGMA table_info(trains)")
    train_cols_after = [r[1] for r in cur.fetchall()]
    assert "loco_class" not in train_cols_after
    assert "rake_type" not in train_cols_after

    cur.execute("PRAGMA table_info(sections)")
    sec_cols_after = [r[1] for r in cur.fetchall()]
    assert "gradient_pct" not in sec_cols_after
    assert "zone_id" not in sec_cols_after

    conn.close()


def test_corridor_data_prep_script():
    """Verifies that populate_domain_corridor.py populates deterministic values."""
    db = get_db()
    from scripts.populate_domain_corridor import populate_domain_features

    populate_domain_features(db)

    with db.transaction() as cur:
        cur.execute("SELECT loco_class, rake_type FROM trains WHERE loco_class IS NOT NULL")
        train_rows = cur.fetchall()
        assert len(train_rows) > 0, "No trains populated with domain features"
        for r in train_rows[:10]:
            assert r["loco_class"] in ("WAP-7", "WAP-5", "WAP-4", "WAG-9")
            assert r["rake_type"] in ("LHB", "ICF", "VANDE_BHARAT", "BOXN")

        cur.execute("SELECT gradient_pct, zone_id FROM sections WHERE gradient_pct IS NOT NULL")
        sec_rows = cur.fetchall()
        assert len(sec_rows) > 0, "No sections populated with domain features"
        for r in sec_rows[:10]:
            assert 0.0 <= r["gradient_pct"] <= 1.0
            assert r["zone_id"] in ("NR", "NCR", "NWR", "WR")


def test_t3_temporal_split_and_snapshot_extraction(tmp_path: Path):
    """GATE T3: Snapshot extraction populates domain features and respects 2-day temporal embargo."""
    db = get_db()
    sg = SnapshotGenerator(db)

    # Extract snapshot
    vec = sg.extract_features_at_snapshot(
        train_no="12301",
        current_seq=1,
        target_seq=2,
        run_date_str="2026-08-25",
        current_delay=10.0,
        prev_delay=5.0,
        query_time_iso="2026-08-25T10:00:00+05:30",
    )

    # Verify domain fields on the extracted vector
    assert vec.loco_class > 0
    assert vec.rake_type > 0
    assert vec.zone_id > 0
    assert vec.sectional_run_time >= 0.0
    assert vec.tsr_delay_min >= 0.0
    assert vec.signal_aspect in (0, 1, 2, 3)
    assert vec.lc_status in (0, 1)

    # Verify 2-day embargo integrity: evaluate rolling origin fold embargo
    from ml.evaluate import Evaluator
    evaluator = Evaluator(db=db)
    folds = evaluator.run_rolling_origin_cv(num_folds=3, embargo_days=2)
    for f in folds:
        if f.get("train_end") and f.get("test_start"):
            import datetime
            d_train_end = datetime.date.fromisoformat(f["train_end"])
            d_test_start = datetime.date.fromisoformat(f["test_start"])
            gap = (d_test_start - d_train_end).days
            # Embargo of 2 days means at least 3 days between train_end and test_start (cal + 2 embargos)
            assert gap >= 3, f"Embargo violated: gap between train_end and test_start is {gap} days"
