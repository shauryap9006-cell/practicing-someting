"""RailTwin-X Physics Digital Twin Verification & Heartbeat Tests (Phase 3).

Verifies:
1. Twin pure-math kinematics (no DB): monotonic km, speed limits, DWELL, TSR capping, signal hold, APPROACH deceleration.
2. Tracker integration: station_events schema, closed-loop ledger grading, multi-station traversal, SSE stream frames with source.
3. Advisory lock: idempotent tracker start/stop preventing double execution.
4. Scoreboard calibration & clock mode consistency (/v1/meta/clock, /v1/health).
"""

import asyncio
import json

from fastapi.testclient import TestClient

from api.main import app
from data.db import get_db
from engine.clocks import set_global_clock
from engine.live_tracker import LivePositionTracker, get_live_tracker
from engine.prediction_ledger import PredictionLedger
from engine.sim_clock import get_sim_clock
from engine.twin import TwinEngine

client = TestClient(app)


def test_twin_pure_math_simulation():
    """Verifies pure mathematical kinematics across 300 simulated minutes @ accel=60."""
    engine = TwinEngine(default_max_speed_kmh=130.0)
    stops = [
        {"station_code": "NDLS", "seq": 1, "distance_km": 0.0, "halt_min": 2, "sched_dep": "10:00"},
        {
            "station_code": "GZB",
            "seq": 2,
            "distance_km": 25.0,
            "halt_min": 2,
            "sched_arr": "10:20",
            "sched_dep": "10:22",
        },
        {
            "station_code": "ALJN",
            "seq": 3,
            "distance_km": 130.0,
            "halt_min": 2,
            "sched_arr": "11:30",
            "sched_dep": "11:32",
        },
    ]
    state = engine.create_train_state(
        "12301", stops, start_km=0.0, start_speed_kmh=0.0, start_phase="DWELL"
    )
    state.dwell_remaining_sec = 60.0

    prev_km = -1.0
    dwell_ticks = 0
    all_events = []

    # 300 simulated minutes (each step = 60 seconds)
    for tick in range(300):
        state, evs = engine.advance(state, dt_seconds=60.0)
        # 1. Monotonic km non-decreasing
        assert state.km >= prev_km, f"km non-monotonic: {state.km} < {prev_km} at tick {tick}"
        prev_km = state.km

        # 2. Speed bounds [0, max * 1.1]
        assert 0.0 <= state.speed_kmh <= 130.0 * 1.1, f"speed out of bounds: {state.speed_kmh}"

        # 3. Dwell check
        if state.phase == "DWELL" and state.speed_kmh == 0.0:
            dwell_ticks += 1

        if evs:
            all_events.extend(evs)

    # Dwell observed for at least 50% of scheduled halt (at least 1 minute = 1 tick)
    assert dwell_ticks >= 1, "DWELL phase with speed==0.0 not observed during simulation"
    assert len(all_events) >= 2, (
        f"Expected at least 2 events (DEPARTURE, ARRIVAL), got {len(all_events)}"
    )

    # 4. TSR_ZONE caps speed
    state_tsr = engine.create_train_state(
        "12301", stops, start_km=10.0, start_speed_kmh=40.0, start_phase="CRUISE"
    )
    state_tsr, _ = engine.advance(state_tsr, dt_seconds=10.0, context={"active_tsr_kmh": 45.0})
    assert state_tsr.speed_kmh <= 45.0 + 1e-5, (
        f"TSR not capping speed: {state_tsr.speed_kmh} > 45.0"
    )
    assert state_tsr.phase == "TSR_ZONE"

    # 5. HELD stops before occupied block
    state_held = engine.create_train_state(
        "12301", stops, start_km=15.0, start_speed_kmh=80.0, start_phase="CRUISE"
    )
    for _ in range(60):
        state_held, _ = engine.advance(
            state_held, dt_seconds=1.0, context={"block_occupied": True, "signal_aspect": "RED"}
        )
    assert state_held.speed_kmh == 0.0, (
        f"Train did not stop when block occupied: speed={state_held.speed_kmh}"
    )
    assert state_held.phase == "HELD"

    # 6. APPROACH decelerates towards station
    state_app = engine.create_train_state(
        "12301", stops, start_km=24.5, start_speed_kmh=100.0, start_phase="CRUISE"
    )
    state_app, _ = engine.advance(state_app, dt_seconds=1.0)
    assert state_app.phase in ("APPROACH", "DWELL"), (
        f"Expected APPROACH phase, got {state_app.phase}"
    )
    assert state_app.speed_kmh < 100.0, "Speed did not decelerate in approach zone"


def test_tracker_advisory_lock_idempotent():
    """Verifies that starting/stopping the tracker is idempotent and prevents double-start loops."""
    tracker = LivePositionTracker(db=get_db())
    assert not tracker.is_running

    async def run_lock_test():
        # First start
        await tracker.start()
        assert tracker.is_running
        task1 = tracker._task
        assert task1 is not None

        # Second start (should be no-op)
        await tracker.start()
        assert tracker.is_running
        assert tracker._task is task1  # No new task spawned

        # Stop
        await tracker.stop()
        assert not tracker.is_running
        assert tracker._task is None

        # Second stop (should be no-op)
        await tracker.stop()
        assert not tracker.is_running

    asyncio.run(run_lock_test())


def test_heartbeat_integration_and_events():
    """Verifies tracker tick produces station_events conforming to 13-column schema and grades ledger."""
    db = get_db()
    sim_clock = get_sim_clock(db)
    set_global_clock(sim_clock)
    tracker = get_live_tracker(db)

    # Execute simulation ticks across several corridor minutes
    async def run_ticks():
        positions = []
        for minute_offset in range(5):
            t_sim = sim_clock.now() + datetime.timedelta(minutes=minute_offset * 10)
            pos_batch = await tracker.tick(as_of_time=t_sim)
            if pos_batch:
                positions.extend(pos_batch)
        return positions

    import datetime

    positions = asyncio.run(run_ticks())
    assert len(positions) > 0, "Tracker produced no live positions"

    # 1. Verify station_events table rows and 13-column schema
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT train_no, run_date, seq, station_code, sched_arr, actual_arr,
                   sched_dep, actual_dep, delay_arr_min, delay_dep_min,
                   collected_at, event_time, source
            FROM station_events
            WHERE source = 'simulated'
            """
        )
        sim_events = cur.fetchall()

    assert len(sim_events) >= 1, f"Expected simulated station_events rows, found {len(sim_events)}"
    sample_ev = dict(sim_events[0])
    assert sample_ev["source"] == "simulated"
    assert sample_ev["train_no"] is not None
    assert sample_ev["station_code"] is not None

    # 2. Verify ledger chain integrity
    ledger = PredictionLedger(db)
    is_valid, total_blocks, broken_id = ledger.verify_chain_integrity()
    assert is_valid is True, f"Ledger broken at block {broken_id}"
    assert total_blocks >= 5134, f"Total blocks {total_blocks} below Phase 0 baseline 5134"

    # 3. Verify positions carry source: simulated
    sample_pos = positions[0]
    assert sample_pos.source == "simulated"
    assert sample_pos.km >= 0.0


def test_meta_clock_and_health_consistency():
    """Verifies /v1/meta/clock and /v1/health both report mode 'simulated'."""
    db = get_db()
    sim_clock = get_sim_clock(db)
    set_global_clock(sim_clock)

    # 1. GET /v1/meta/clock
    resp_clock = client.get("/v1/meta/clock")
    assert resp_clock.status_code == 200
    data_clock = resp_clock.json()
    assert data_clock["mode"] == "simulated"
    assert "sim_now" in data_clock
    assert "real_now" in data_clock
    assert "accel" in data_clock

    # 2. GET /v1/health
    resp_health = client.get("/v1/health")
    assert resp_health.status_code in (200, 503)
    data_health = resp_health.json()
    assert data_health["clock_mode"] == "simulated", (
        f"Expected 'simulated', got {data_health['clock_mode']}"
    )


def test_sse_live_stream_smoke():
    """Verifies Server-Sent Events /v1/live/stream produces JSON frames carrying source."""
    resp = client.get("/v1/live/stream?max_frames=1")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    lines = [line.strip() for line in resp.text.split("\n") if line.startswith("data:")]
    assert len(lines) >= 1, f"Expected at least 1 SSE data frame, got {len(lines)}"

    payload = json.loads(lines[0][5:].strip())
    assert "event" in payload
    assert "positions" in payload
    if payload["positions"]:
        assert "source" in payload["positions"][0]
