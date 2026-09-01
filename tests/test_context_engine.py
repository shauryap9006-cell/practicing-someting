"""Unit and Integration Tests for RailTwin-X ContextEngine (Pipeline 07, Phase A4)."""

import datetime
import pytest

from config import settings
from data.db import Database, get_db
from engine.clocks import RealClock, ReplayClock, set_global_clock
from engine.context import ContextEngine, TrainContext, get_context_engine


@pytest.fixture
def db():
    database = get_db()
    database.init_schema()
    return database


@pytest.fixture
def context_engine(db):
    return ContextEngine(db)


def test_context_engine_initialization(context_engine):
    """Verifies ContextEngine initializes with valid components and caching."""
    assert context_engine is not None
    assert context_engine.cache_ttl == float(settings.CONTEXT_CACHE_TTL_SECONDS)
    singleton = get_context_engine()
    assert singleton is not None


def test_enrich_5_layers_known_train(context_engine):
    """Verifies complete 5-layer enrichment for a known corridor train."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    ctx = context_engine.get_train_context(
        train_no="12301",
        run_date=today_str,
        current_station_code="CNB",
        current_km=440.0,
        force_refresh=True,
    )

    assert isinstance(ctx, TrainContext)
    assert ctx.train_no == "12301"
    assert ctx.run_date == today_str
    assert ctx.current_station_code == "CNB"
    assert ctx.current_km == 440.0

    # Layer 1: Weather
    assert ctx.weather is not None
    assert ctx.weather.station_code == "CNB"
    assert isinstance(ctx.weather.temp_celsius, float)
    assert isinstance(ctx.weather.humidity_pct, float)
    assert isinstance(ctx.weather.precip_mm, float)
    assert ctx.weather.fog_flag in (0, 1)
    assert ctx.weather.visibility_km > 0.0
    assert len(ctx.weather.summary) > 0

    # Layer 2: TSRs
    assert isinstance(ctx.active_tsrs, list)
    for tsr in ctx.active_tsrs:
        assert tsr.speed_limit_kmph > 0
        assert tsr.delay_penalty_min >= 0.0
        assert len(tsr.cause) > 0

    # Layer 3: Rake Turnaround Doom
    assert ctx.rake is not None
    assert isinstance(ctx.rake.has_rake_link, bool)
    assert ctx.rake.turnaround_deficit_min >= 0
    assert isinstance(ctx.rake.is_doomed, bool)

    # Layer 4: Platform
    assert ctx.platform is not None
    assert ctx.platform.station_code == "CNB"
    assert ctx.platform.platform >= 1
    assert ctx.platform.dwell_min >= 1
    assert isinstance(ctx.platform.is_conflicted, bool)

    # Layer 5: Spatial Congestion
    assert ctx.spatial is not None
    assert ctx.spatial.trains_ahead_30k >= 0
    assert ctx.spatial.trains_behind_30k >= 0
    assert ctx.spatial.section_occupancy_pct >= 0.0
    assert isinstance(ctx.spatial.is_congested, bool)


def test_context_engine_caching_performance(context_engine):
    """Verifies that second retrieval within TTL hits in-memory cache."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # First call: populates cache
    ctx1 = context_engine.get_train_context("12301", today_str, "NDLS", 0.0, force_refresh=True)
    
    # Second call: fast cache hit
    start_time = datetime.datetime.now()
    ctx2 = context_engine.get_train_context("12301", today_str, "NDLS", 0.0, force_refresh=False)
    elapsed_ms = (datetime.datetime.now() - start_time).total_seconds() * 1000.0

    assert ctx1.timestamp == ctx2.timestamp
    assert elapsed_ms < 50.0  # In-memory retrieval under 50ms


def test_context_cache_invalidation(context_engine):
    """Verifies cache invalidation clears specific or all cached entries."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    context_engine.get_train_context("12301", today_str, "NDLS", 0.0, force_refresh=True)
    context_engine.get_train_context("12302", today_str, "DDU", 785.0, force_refresh=True)

    assert len(context_engine._cache) >= 2

    # Invalidate specific train
    context_engine.invalidate_cache("12301")
    assert not any(k.startswith("12301:") for k in context_engine._cache)
    assert any(k.startswith("12302:") for k in context_engine._cache)

    # Invalidate all
    context_engine.invalidate_cache()
    assert len(context_engine._cache) == 0


def test_context_to_dict_serialization(context_engine):
    """Verifies JSON-safe dictionary serialization of TrainContext."""
    ctx = context_engine.get_train_context("12301", "2026-08-31", "ETW", 301.0, force_refresh=True)
    payload = ctx.to_dict()

    assert payload["train_no"] == "12301"
    assert payload["run_date"] == "2026-08-31"
    assert payload["current_station_code"] == "ETW"
    assert "weather" in payload
    assert "active_tsrs" in payload
    assert "rake" in payload
    assert "platform" in payload
    assert "spatial" in payload
    assert isinstance(payload["weather"]["summary"], str)
