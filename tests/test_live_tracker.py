"""Unit and Integration Tests for RailTwin-X LivePositionTracker (Pipeline 07, Phase A3)."""

import asyncio
import datetime
import pytest

from config import settings
from data.db import Database, get_db
from engine.clocks import RealClock, ReplayClock, set_global_clock
from engine.live_tracker import LivePositionTracker, TokenBucket, get_live_tracker, _calculate_heading


@pytest.fixture
def db():
    database = get_db()
    database.init_schema()
    return database


@pytest.fixture
def tracker(db):
    return LivePositionTracker(db)


def test_tracker_initialization(tracker):
    """Verifies LivePositionTracker initializes with config-fed parameters."""
    assert tracker is not None
    assert tracker.tick_interval == float(settings.LIVE_TRACKER_INTERVAL_SECONDS)
    assert tracker.tau == float(settings.CONFIDENCE_TAU_SECONDS)
    assert tracker.min_confidence == float(settings.DEAD_RECKON_MIN_CONFIDENCE)
    singleton = get_live_tracker()
    assert singleton is not None


def test_token_bucket_rate_limiter():
    """Verifies token bucket enforces capacity limit and consumption."""
    tb = TokenBucket(capacity=5, fill_rate_per_second=1.0)
    assert tb.consume(3) is True
    assert tb.consume(2) is True
    assert tb.consume(1) is False  # Exhausted


def test_calculate_heading():
    """Verifies geographic bearing calculation between coordinates."""
    # North heading
    h_north = _calculate_heading(28.0, 77.0, 29.0, 77.0)
    assert abs(h_north - 0.0) < 1.0 or abs(h_north - 360.0) < 1.0

    # East heading
    h_east = _calculate_heading(28.0, 77.0, 28.0, 78.0)
    assert abs(h_east - 90.0) < 2.0


def test_polyline_dead_reckoning_interpolation(tracker):
    """Verifies continuous polyline coordinate and progress calculation along corridor."""
    pos = tracker.get_live_position("12301")
    assert pos is not None
    assert pos["train_no"] == "12301"
    assert 25.0 <= pos["lat"] <= 29.0  # Corridor lat range
    assert 77.0 <= pos["lng"] <= 83.5  # Corridor lon range
    assert 0.0 <= pos["progress_pct"] <= 100.0
    assert 0.0 <= pos["confidence"] <= 1.0
    assert pos["status"] in ("RUNNING", "TERMINATED", "NOT_STARTED", "STALE")


@pytest.mark.asyncio
async def test_tracker_tick_and_persistence(tracker, db):
    """Verifies tracker tick computes live positions and persists into SQLite table."""
    positions = await tracker.tick(train_limit=10)
    assert len(positions) > 0

    # Verify rows exist in SQLite live_positions table
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) FROM live_positions")
        count = cur.fetchone()[0]
        assert count > 0

    # Verify get_all_live_positions
    all_positions = tracker.get_all_live_positions()
    assert len(all_positions) > 0


@pytest.mark.asyncio
async def test_listener_subscription_and_broadcast(tracker):
    """Verifies async queues and callback listeners receive position broadcasts."""
    queue = asyncio.Queue()
    received_callbacks = []

    def callback_listener(payload):
        received_callbacks.append(payload)

    tracker.subscribe(queue)
    tracker.subscribe(callback_listener)

    # Broadcast test update
    test_payload = {"event": "test_event", "value": 42}
    await tracker._broadcast(test_payload)

    # Verify queue received payload
    queued_item = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert queued_item["event"] == "test_event"
    assert queued_item["value"] == 42

    # Verify callback received payload
    assert len(received_callbacks) == 1
    assert received_callbacks[0]["event"] == "test_event"

    tracker.unsubscribe(queue)
    tracker.unsubscribe(callback_listener)
