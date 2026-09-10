"""WO-01 Reproducer Test: Verifying Live Ingestion Adapter Wiring in LivePositionTracker.

Tests the defect where self.adapters was instantiated in __init__ but never invoked in tick(),
and source was never set to 'live' or validated via QualityGate.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from collector.adapters.base import LiveSource, StationEvent
from config import settings
from data.db import get_db
from engine.live_tracker import LivePositionTracker


class DummyLiveSource(LiveSource):
    def __init__(self, name: str = "DummyLive", events=None):
        self._name = name
        self.events = events or []
        self.call_count = 0

    @property
    def source_name(self) -> str:
        return self._name

    def fetch_running_status(self, train_no: str, run_date: datetime.date) -> list[StationEvent]:
        self.call_count += 1
        return self.events


@pytest.fixture
def test_db():
    db = get_db()
    db.init_schema()
    return db


@pytest.mark.asyncio
async def test_live_tracker_polls_adapters_and_tags_live_source(test_db):
    """GATE-1 Reproducer: Verify tick() calls adapters and tags source as 'live' when telemetry is received."""
    today_str = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().isoformat()

    live_events = [
        StationEvent(
            train_no="12301",
            run_date=today_str,
            seq=1,
            station_code="NDLS",
            sched_dep="16:50",
            actual_dep="16:55",
            delay_dep_min=5,
            collected_at=now_iso,
        ),
        StationEvent(
            train_no="12301",
            run_date=today_str,
            seq=2,
            station_code="CNB",
            sched_arr="21:30",
            actual_arr="21:40",
            delay_arr_min=10,
            collected_at=now_iso,
        ),
    ]

    mock_adapter = DummyLiveSource(name="RapidAPI", events=[])
    tracker = LivePositionTracker(db=test_db, adapters=[mock_adapter])
    target_train = tracker._get_active_corridor_trains(limit=1)[0]

    live_events = [
        StationEvent(
            train_no=target_train,
            run_date=today_str,
            seq=1,
            station_code="NDLS",
            sched_dep="16:50",
            actual_dep="16:55",
            delay_dep_min=5,
            collected_at=now_iso,
        ),
        StationEvent(
            train_no=target_train,
            run_date=today_str,
            seq=2,
            station_code="CNB",
            sched_arr="21:30",
            actual_arr="21:40",
            delay_arr_min=10,
            collected_at=now_iso,
        ),
    ]
    mock_adapter.events = live_events

    # Tick with train limit 1
    with patch.object(settings, "LIVE_SOURCE_MODE", "live"):
        positions = await tracker.tick(train_limit=1)

    assert len(positions) > 0
    # Must have polled the adapter
    assert mock_adapter.call_count > 0, "Adapters were never polled during tick()!"

    # Position for target train must reflect live ingestion
    pos_target = next((p for p in positions if p.train_no == target_train), None)
    assert pos_target is not None
    assert pos_target.source == "live", f"Expected source='live' but got '{pos_target.source}'"


@pytest.mark.asyncio
async def test_live_tracker_falls_back_to_physics_twin_when_adapter_fails(test_db):
    """GATE-1 Reproducer: When adapter throws an exception or returns empty, tracker falls back to simulation."""
    failing_adapter = DummyLiveSource(name="FailingSource", events=[])

    def raise_err(train_no, run_date):
        failing_adapter.call_count += 1
        raise ConnectionError("Upstream API unreachable")

    failing_adapter.fetch_running_status = raise_err

    tracker = LivePositionTracker(db=test_db, adapters=[failing_adapter])
    target_train = tracker._get_active_corridor_trains(limit=1)[0]

    with patch.object(settings, "LIVE_SOURCE_MODE", "live"):
        positions = await tracker.tick(train_limit=1)

    assert failing_adapter.call_count > 0
    assert len(positions) > 0
    pos_target = next((p for p in positions if p.train_no == target_train), None)
    assert pos_target is not None
    # Must fallback gracefully to simulation/replay
    assert pos_target.source in ("simulated", "mock_replay", "fallback_simulated")
