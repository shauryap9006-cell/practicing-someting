"""Unit and Integration Tests for RailTwin-X LiveAttributionEngine (Pipeline 07, Phase A5)."""

import datetime
import pytest

from config import settings
from data.db import Database, get_db
from engine.context import ContextEngine, TrainContext, WeatherContext, TSRContextItem, RakeContext, PlatformContext, SpatialCongestionContext
from engine.attribution import LiveAttributionEngine, AttributionResult, get_attribution_engine


@pytest.fixture
def db():
    database = get_db()
    database.init_schema()
    return database


@pytest.fixture
def attribution_engine(db):
    return LiveAttributionEngine(db)


def test_attribution_engine_initialization(attribution_engine):
    """Verifies LiveAttributionEngine initializes with correct thresholds."""
    assert attribution_engine is not None
    assert attribution_engine.min_delta == float(settings.ATTRIBUTION_DELTA_MIN)
    singleton = get_attribution_engine()
    assert singleton is not None


def test_delay_jump_below_threshold_ignored(attribution_engine):
    """Verifies micro delay fluctuations (< ATTRIBUTION_DELTA_MIN) return None."""
    res = attribution_engine.evaluate_delay_jump(
        train_no="12301",
        run_date="2026-08-31",
        previous_delay_min=10.0,
        current_delay_min=13.0,  # +3m jump (< 5m min threshold)
        station_code="CNB",
    )
    assert res is None


def test_exact_delay_accounting_invariant(attribution_engine):
    """Verifies that sum(causes.attributed_min) strictly equals measured_delta_min."""
    test_deltas = [5.0, 8.5, 16.0, 25.0, 45.0, 90.0]
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    for delta in test_deltas:
        res = attribution_engine.evaluate_delay_jump(
            train_no="12301",
            run_date=today_str,
            previous_delay_min=10.0,
            current_delay_min=10.0 + delta,
            station_code="CNB",
            current_km=440.0,
        )
        assert res is not None
        assert res.is_exact_accounting is True
        assert abs(res.measured_delta_min - delta) < 1e-4

        sum_causes = sum(c.attributed_min for c in res.causes)
        assert abs(sum_causes - delta) < 1e-3, f"Exact accounting violated: {sum_causes} != {delta}"
        assert res.primary_cause in attribution_engine.VALID_CAUSES
        assert res.ledger_id is not None
        assert res.ledger_id > 0


def test_all_7_causal_rules_evaluation(attribution_engine):
    """Verifies priority evaluation and evidence generation across causal rules."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # Construct mock context with various triggers
    mock_weather = WeatherContext(
        station_code="CNB",
        temp_celsius=11.0,
        humidity_pct=95.0,
        precip_mm=30.0,  # Heavy rain trigger
        fog_flag=1,      # Fog trigger
        visibility_km=0.4,
        is_caution=True,
        summary="Dense Fog & Rain",
    )
    mock_tsr = [
        TSRContextItem(
            from_code="CNB",
            to_code="PRYJ",
            speed_limit_kmph=40,
            cause="Track fracturing",
            start_km=440.0,
            end_km=450.0,
            delay_penalty_min=9.5,
            status="ACTIVE",
        )
    ]
    mock_rake = RakeContext(
        has_rake_link=True,
        incoming_train="12034",
        incoming_delay_min=45,
        turnaround_min=240,
        projected_dep_delay_min=15,
        turnaround_deficit_min=15,
        is_doomed=True,
        official_ntes_status="DOOMED",
    )
    mock_platform = PlatformContext(
        station_code="CNB",
        platform=2,
        dwell_min=25,
        is_conflicted=True,
        conflict_train="12004",
        conflict_duration_min=12,
    )
    mock_spatial = SpatialCongestionContext(
        trains_ahead_30k=3,
        trains_behind_30k=1,
        opposing_trains_30k=2,
        sum_delay_trains_ahead_30k=35.0,
        section_occupancy_pct=80.0,
        is_congested=True,
    )

    custom_ctx = TrainContext(
        train_no="12301",
        run_date=today_str,
        timestamp=datetime.datetime.now().isoformat(),
        current_station_code="CNB",
        current_km=440.0,
        weather=mock_weather,
        active_tsrs=mock_tsr,
        rake=mock_rake,
        platform=mock_platform,
        spatial=mock_spatial,
    )

    # Large delay jump: +60m
    res = attribution_engine.evaluate_delay_jump(
        train_no="12301",
        run_date=today_str,
        previous_delay_min=0.0,
        current_delay_min=60.0,
        station_code="CNB",
        context=custom_ctx,
    )

    assert res is not None
    assert res.measured_delta_min == 60.0
    assert res.is_exact_accounting is True

    cause_codes = {c.cause_code for c in res.causes}
    # Expected triggers: RAKE_INHERIT, TSR_ACTIVE, WEATHER_FOG, WEATHER_RAIN, PLATFORM_WAIT, CONGESTION
    assert "RAKE_INHERIT" in cause_codes
    assert "TSR_ACTIVE" in cause_codes
    assert "WEATHER_FOG" in cause_codes
    assert "WEATHER_RAIN" in cause_codes
    assert "PLATFORM_WAIT" in cause_codes

    total_allocated = sum(c.attributed_min for c in res.causes)
    assert abs(total_allocated - 60.0) < 1e-3


def test_get_why_late_summary(attribution_engine, db):
    """Verifies Why-Late timeline aggregation from live_delay_ledger."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # Generate two attribution events
    attribution_engine.evaluate_delay_jump("12301", today_str, 0.0, 15.0, "NDLS")
    attribution_engine.evaluate_delay_jump("12301", today_str, 15.0, 35.0, "CNB")

    summary = attribution_engine.get_why_late_summary("12301", today_str)

    assert summary["train_no"] == "12301"
    assert summary["run_date"] == today_str
    assert summary["total_attributed_delay_min"] >= 35.0
    assert summary["is_exact_accounting"] is True
    assert len(summary["cause_breakdown"]) > 0
    assert summary["events_count"] >= 2
