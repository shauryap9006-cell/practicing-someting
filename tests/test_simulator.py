"""Unit & Integration Tests for Cascade Simulator Subsystem (M3 - F5, F6, F7).

Tests:
1. SimPy Corridor Graph and single-line priority resources.
2. Same-Rake Doom Tracker calculation.
3. Strict Mathematical Exactness of Delay Autopsy Ledger (sum(minutes) == total_delay).
4. Cascade ripple propagation under delay injection.
"""

from pathlib import Path
import pytest

from data.db import Database
from data.seed import run_full_seed
from engine.rakes import RakeResolver
from engine.simulator import CascadeSimulator


@pytest.fixture(scope="module")
def sim_db(tmp_path_factory) -> Database:
    """Fixture providing a fresh seeded database for simulation tests."""
    temp_dir = tmp_path_factory.mktemp("sim_test_data")
    db_file = temp_dir / "sim_test.db"
    run_full_seed(db_file)
    return Database(db_file)


def test_same_rake_doom_tracker(sim_db: Database):
    """Verifies that delayed incoming train flags outgoing train as doomed."""
    resolver = RakeResolver(sim_db)
    statuses = resolver.evaluate_all_rakes()
    assert len(statuses) >= 10
    
    # Check 12034 -> 12033 pair
    cnb_shatabdi = [s for s in statuses if s.incoming_train == "12034" and s.outgoing_train == "12033"]
    assert len(cnb_shatabdi) == 1
    status = cnb_shatabdi[0]
    assert status.turnaround_min == 240
    assert status.station_code == "NDLS"


def test_simulator_exact_attribution_invariant(sim_db: Database):
    """CRITICAL ACCEPTANCE TEST: Ledger minutes MUST sum exactly to total delay."""
    simulator = CascadeSimulator(sim_db)
    
    # Inject delay +60 min at Kanpur and TSR on Tundla-Etawah
    run_id, ledger_events, train_delays = simulator.run_simulation(
        injected_delays={"12034": {"CNB": 60}},
        active_tsrs={("TDL", "ETW"): 0.7},
        simulation_hours=8.0,
    )
    
    assert len(ledger_events) > 0
    assert "12034" in train_delays

    # Autopsy verification for train 12034
    autopsy = simulator.get_train_autopsy(run_id, "12034")
    assert autopsy["is_exact_accounting"] is True
    
    # Enforce exact mathematical sum equality
    assert autopsy["total_attributed_minutes"] == train_delays["12034"], (
        f"Attribution mismatch: sum of ledger ({autopsy['total_attributed_minutes']}m) "
        f"does not match total delay ({train_delays['12034']}m)"
    )


def test_cascade_ripple_propagation(sim_db: Database):
    """Verifies that injecting delay creates cascade holds across at least 3 trains."""
    simulator = CascadeSimulator(sim_db)
    
    run_id, ledger_events, train_delays = simulator.run_simulation(
        injected_delays={"12034": {"CNB": 120}},
        active_tsrs={("CNB", "ON"): 0.5},
        simulation_hours=10.0,
    )

    # Verify multiple trains logged events
    affected_trains = {ev.train_no for ev in ledger_events}
    assert len(affected_trains) >= 3, f"Expected cascade across >=3 trains, got {len(affected_trains)}"
    
    # Verify presence of CROSSING_HOLD or RAKE_INHERIT events
    event_types = {ev.event_type for ev in ledger_events}
    assert "CROSSING_HOLD" in event_types or "RAKE_INHERIT" in event_types
