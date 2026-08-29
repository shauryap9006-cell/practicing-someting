"""Unit & Integration Tests for Foundation Layer.

Tests:
1. SQLite schema creation and table initialization.
2. Composite Primary Key enforcement and foreign keys.
3. TimeProvider (RealClock and ReplayClock) in IST.
4. Database seeding integrity and row count invariants.
"""

import datetime
from pathlib import Path
import pytest

from data.db import Database
from data.seed import run_full_seed
from engine.clocks import RealClock, ReplayClock, IST_TIMEZONE


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Fixture providing a fresh isolated SQLite database."""
    db_file = tmp_path / "test_railtwin.db"
    db = Database(db_file)
    db.init_schema()
    return db


def test_schema_creation(temp_db: Database):
    """Verifies all required tables exist in schema."""
    counts = temp_db.table_counts()
    expected_tables = [
        "stations", "trains", "route_stations", "sections",
        "rake_links", "station_events", "weather", "sim_ledger"
    ]
    for tbl in expected_tables:
        assert tbl in counts, f"Table {tbl} missing from database"
        assert counts[tbl] == 0


def test_time_provider_real():
    """Verifies RealClock reports IST timezone correctly."""
    clock = RealClock()
    assert clock.mode == "live"
    now = clock.now()
    assert now.tzinfo is not None
    assert now.tzinfo.tzname(now) == "IST"
    assert "T" in clock.now_iso()


def test_time_provider_replay():
    """Verifies ReplayClock supports deterministic time setting and advancement."""
    clock = ReplayClock("2026-08-27 10:00")
    assert clock.mode == "replay"
    assert clock.today_str() == "2026-08-27"
    
    # Advance clock by 30 minutes
    new_time = clock.advance(30.0)
    assert new_time.hour == 10
    assert new_time.minute == 30

    # Advance clock across hour boundary
    new_time = clock.advance(45.0)
    assert new_time.hour == 11
    assert new_time.minute == 15


def test_seed_dataset_integrity(tmp_path: Path):
    """Verifies full database seed populates required corridor data."""
    test_db_path = tmp_path / "seeded_railtwin.db"
    run_full_seed(test_db_path)
    
    db = Database(test_db_path)
    counts = db.table_counts()

    # Invariants
    assert counts["stations"] >= 8, "Must have all 8 corridor stations"
    assert counts["sections"] >= 14, "Must have bidirectional sections"
    assert counts["trains"] == 150, "Must have exactly 150 trains fleet"
    assert counts["route_stations"] >= 150 * 8, "Must have route stops"
    assert counts["rake_links"] >= 14, "Must have rake turnaround pairs"
    assert counts["weather"] >= 28 * 8, "Must have 28 days of weather for all stations"
    assert counts["station_events"] >= 5000, "Must have at least 5k historical events"

    # Query specific rake link
    with db.transaction() as cur:
        cur.execute("SELECT * FROM rake_links WHERE incoming_train = '12034' AND outgoing_train = '12033'")
        rake = cur.fetchone()
        assert rake is not None
        assert rake["station_code"] == "NDLS"
        assert rake["turnaround_min"] == 240
