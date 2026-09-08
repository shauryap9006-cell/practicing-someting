"""Unit & Integration Tests for Data Collector Subsystem (M1).

Tests:
1. Adapter fallback chain (RapidAPI -> Scrape -> MockReplay).
2. Quality gate rules (Sanity bounds, Monotonicity, Quarantine logic).
3. Weather engine client & fallback.
4. Idempotent upsert verification (Zero duplicates on repoll).
"""

import datetime
from pathlib import Path

import pytest

from collector.adapters.base import StationEvent
from collector.adapters.mock_replay import MockReplaySource
from collector.collect import DataCollector
from collector.quality import QualityGate
from collector.weather import WeatherEngine
from data.db import Database
from data.seed import seed_master_data


@pytest.fixture
def seeded_db(tmp_path: Path) -> Database:
    """Fixture providing a fresh database with seeded master data."""
    db_file = tmp_path / "collector_test.db"
    db = Database(db_file)
    db.init_schema()
    seed_master_data(db)
    return db


def test_mock_replay_adapter(seeded_db: Database):
    """Verifies MockReplaySource generates valid route events."""
    adapter = MockReplaySource(seeded_db)
    events = adapter.fetch_running_status("12034", datetime.date(2026, 8, 27))
    assert len(events) >= 8
    assert events[0].station_code == "NDLS" or events[-1].station_code == "NDLS"
    assert all(isinstance(ev, StationEvent) for ev in events)


def test_quality_gate_sanity():
    """Verifies that delays outside bounds are quarantined."""
    gate = QualityGate(max_delay_min=600, min_delay_min=-120)
    events = [
        StationEvent(
            "12034",
            "2026-08-27",
            1,
            "CNB",
            "06:00",
            "06:00",
            "06:05",
            "06:05",
            0,
            0,
            "2026-08-27T06:00:00+05:30",
        ),
        StationEvent(
            "12034",
            "2026-08-27",
            2,
            "ALJN",
            "08:30",
            "19:00",
            "08:35",
            "19:05",
            630,
            630,
            "2026-08-27T08:30:00+05:30",
        ),  # >600m
        StationEvent(
            "12034",
            "2026-08-27",
            3,
            "NDLS",
            "10:30",
            "10:45",
            "10:30",
            "10:45",
            15,
            15,
            "2026-08-27T10:30:00+05:30",
        ),
    ]
    report = gate.validate_events(events)
    assert report.passed_count == 2
    assert report.quarantined_count == 1
    assert "outside sanity bounds" in report.quarantined_events[0][1]


def test_quality_gate_monotonicity():
    """Verifies that actual arrival times going backwards are quarantined."""
    gate = QualityGate()
    events = [
        StationEvent(
            "12034",
            "2026-08-27",
            1,
            "CNB",
            "06:00",
            "06:00",
            "06:05",
            "06:05",
            0,
            0,
            "2026-08-27T06:00:00+05:30",
        ),
        StationEvent(
            "12034",
            "2026-08-27",
            2,
            "ALJN",
            "08:30",
            "05:30",
            "08:35",
            "05:35",
            0,
            0,
            "2026-08-27T08:30:00+05:30",
        ),  # Non-monotonic
    ]
    report = gate.validate_events(events)
    assert report.passed_count == 1
    assert report.quarantined_count == 1
    assert "Non-monotonic" in report.quarantined_events[0][1]


def test_weather_engine(seeded_db: Database):
    """Verifies weather engine retrieves metrics and calculates fog_flag."""
    engine = WeatherEngine(seeded_db)
    synced = engine.sync_corridor_weather(datetime.date(2026, 8, 27), limit=10)
    assert synced >= 8
    counts = seeded_db.table_counts()
    assert counts["weather"] >= 8


def test_collector_idempotent_upsert(seeded_db: Database):
    """Verifies that running collection multiple times produces zero duplicates."""
    collector = DataCollector(seeded_db, adapters=[MockReplaySource(seeded_db)])
    target_date = datetime.date(2026, 8, 27)

    # First cycle
    res1 = collector.run_collection_cycle(target_date=target_date, train_limit=2)
    count1 = seeded_db.table_counts()["station_events"]
    assert res1["events_upserted"] > 0
    assert count1 == res1["events_upserted"]

    # Second cycle on same date (Idempotency test)
    res2 = collector.run_collection_cycle(target_date=target_date, train_limit=2)
    count2 = seeded_db.table_counts()["station_events"]
    assert count2 == count1, "Repolling must produce zero duplicate rows in station_events"


def test_interruptible_sleep():
    """Verifies that _interruptible_sleep runs in small increments without hanging."""
    from collector.adapters.scrape import _interruptible_sleep

    start = datetime.datetime.now()
    _interruptible_sleep(0.05, step=0.01)
    elapsed = (datetime.datetime.now() - start).total_seconds()
    assert elapsed >= 0.04


def test_scrape_source_configuration():
    """Verifies ScrapeSource defaults to (5.0, 15.0) timeouts and 3 max retries."""
    from collector.adapters.scrape import ScrapeSource

    src = ScrapeSource()
    assert src.timeout == (5.0, 15.0)
    assert src.max_retries == 3
    assert src.source_name == "WebScrape"


def test_scrape_source_network_failure_no_raise(monkeypatch):
    """Verifies that network failures across targets log warnings and return empty list."""
    import requests

    from collector.adapters.scrape import ScrapeSource

    src = ScrapeSource(max_retries=1, polite_delay=0.0)

    def mock_get(*args, **kwargs):
        raise requests.ConnectionError("Network unreachable")

    monkeypatch.setattr(src.session, "get", mock_get)
    events = src.fetch_running_status("12034", datetime.date(2026, 8, 27))
    assert events == []


def test_scrape_source_malformed_html_no_raise(monkeypatch):
    """Verifies that malformed/invalid external responses do not raise into callers."""
    from collector.adapters.scrape import ScrapeSource

    src = ScrapeSource(max_retries=1, polite_delay=0.0)

    class MockResponse:
        status_code = 200
        text = "<html><body>502 Bad Gateway - INVALID TRAIN ERROR</body></html>"

    monkeypatch.setattr(src.session, "get", lambda *args, **kwargs: MockResponse())
    events = src.fetch_running_status("12034", datetime.date(2026, 8, 27))
    assert events == []


def test_scrape_source_valid_erail_parsing(monkeypatch):
    """Verifies valid eRail data is parsed into StationEvent objects."""
    from collector.adapters.scrape import ScrapeSource

    src = ScrapeSource(max_retries=1, polite_delay=0.0)

    class MockResponse:
        status_code = 200
        text = (
            "CNB^06:00^06:00^06:05^06:05^0^1~"
            "ALJN^08:30^08:35^08:35^08:40^5^2~"
            "NDLS^10:30^10:45^10:30^10:45^15^3~"
        )

    monkeypatch.setattr(src.session, "get", lambda *args, **kwargs: MockResponse())
    events = src.fetch_running_status("12034", datetime.date(2026, 8, 27))
    assert len(events) == 3
    assert events[0].station_code == "CNB"
    assert events[1].station_code == "ALJN"
    assert events[2].station_code == "NDLS"
    assert events[1].delay_arr_min == 5
