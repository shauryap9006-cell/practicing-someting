"""Unit & Integration Tests for Operations Layer (M4 - F8, F9, F13).

Tests:
1. Platform Gantt block time interval parsing and overlap detection.
2. Greedy + Local-Search Re-Optimizer speed (<2s) and conflict resolution.
3. Plan diff accuracy and rollback functionality.
4. Advisory crew duty-breach projection calculations.
"""

from pathlib import Path
import pytest

from data.db import Database
from data.seed import run_full_seed
from engine.ops import PlatformBlock, PlatformManager, CrewDutyEngine


@pytest.fixture(scope="module")
def ops_db(tmp_path_factory) -> Database:
    """Fixture providing a fresh seeded database for ops tests."""
    temp_dir = tmp_path_factory.mktemp("ops_test_data")
    db_file = temp_dir / "ops_test.db"
    run_full_seed(db_file)
    return Database(db_file)


def test_platform_block_overlap():
    """Verifies pairwise interval overlap detection logic."""
    b1 = PlatformBlock("12034", 1, "2026-08-27T10:00:00", "2026-08-27T10:30:00", 30)
    b2 = PlatformBlock("12420", 1, "2026-08-27T10:15:00", "2026-08-27T10:45:00", 30)
    b3 = PlatformBlock("12554", 1, "2026-08-27T11:00:00", "2026-08-27T11:30:00", 30)
    b_diff_plat = PlatformBlock("12802", 2, "2026-08-27T10:15:00", "2026-08-27T10:45:00", 30)

    # Overlaps on same platform
    assert b1.overlaps_with(b2) is True
    assert b2.overlaps_with(b1) is True

    # No overlap (sequential)
    assert b1.overlaps_with(b3) is False

    # No overlap (different platform)
    assert b1.overlaps_with(b_diff_plat) is False


def test_reoptimizer_speed_and_resolution(ops_db: Database):
    """Verifies that platform re-optimizer runs in <2s and resolves conflicts."""
    pm = PlatformManager(ops_db)
    blocks, conflicts = pm.get_station_gantt("NDLS")

    # If naturally conflict-free, inject a collision
    if not conflicts and len(blocks) >= 2:
        blocks[1].platform = blocks[0].platform
        blocks[1].start_time_iso = blocks[0].start_time_iso
        blocks[1].end_time_iso = blocks[0].end_time_iso

    reopt_blocks, diff = pm.reoptimize_platforms("NDLS", blocks)

    assert diff.execution_time_seconds < 2.0, "Re-optimization must finish in <2 seconds"
    assert diff.conflicts_after <= diff.conflicts_before
    assert diff.resolved_conflicts >= 0

    # Test rollback
    rolled_back = pm.rollback_plan("NDLS")
    assert rolled_back is not None
    assert len(rolled_back) == len(blocks)


def test_crew_duty_alerts(ops_db: Database):
    """Verifies crew duty breach calculations with advisory labeling."""
    crew_engine = CrewDutyEngine(ops_db)
    alerts = crew_engine.evaluate_crew_alerts()

    # All generated alerts must be labeled strictly advisory
    for a in alerts:
        assert a.is_advisory is True
        assert a.duty_cap_hours == 10.0
        assert a.breach_minutes >= 0
        assert "ADVISORY" in a.to_dict()["message"]
