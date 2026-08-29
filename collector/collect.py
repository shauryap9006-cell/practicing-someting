"""RailTwin-X Data Collector Service & Cron Entrypoint.

Orchestrates multi-adapter failover (RapidAPI -> WebScrape -> MockReplay),
validates quality gates, and idempotently upserts running status into SQLite.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from config import settings
from collector.adapters.base import LiveSource, StationEvent
from collector.adapters.rapidapi import RapidAPISource
from collector.adapters.scrape import ScrapeSource
from collector.adapters.mock_replay import MockReplaySource
from collector.quality import QualityGate
from collector.weather import WeatherEngine
from data.db import Database, get_db
from engine.clocks import get_clock


class DataCollector:
    """Orchestrator for automated corridor train data collection."""

    def __init__(self, db: Optional[Database] = None, adapters: Optional[List[LiveSource]] = None):
        self.db = db or get_db()
        self.quality_gate = QualityGate()
        self.weather_engine = WeatherEngine(self.db)

        # 3-Tier Adapter Chain
        self.adapters: List[LiveSource] = adapters if adapters is not None else [
            RapidAPISource(),
            ScrapeSource(),
            MockReplaySource(self.db),
        ]

    def fetch_with_failover(
        self, train_no: str, run_date: datetime.date
    ) -> tuple[List[StationEvent], str]:
        """Attempts collection through adapter chain until success."""
        for adapter in self.adapters:
            try:
                events = adapter.fetch_running_status(train_no, run_date)
                if events:
                    return events, adapter.source_name
            except Exception:
                # Silently proceed to next adapter in chain
                continue

        # If all fail, mock source guaranteed
        mock_src = MockReplaySource(self.db)
        return mock_src.fetch_running_status(train_no, run_date), mock_src.source_name

    def run_collection_cycle(
        self, target_date: Optional[datetime.date] = None, train_limit: Optional[int] = None
    ) -> dict:
        """Executes a complete collection run for corridor trains."""
        clock = get_clock()
        run_date = target_date or clock.now().date()
        date_str = run_date.strftime("%Y-%m-%d")

        print(f"[INFO] Starting collection cycle for {date_str} (Mode: {clock.mode})...")

        # 1. Sync corridor weather first
        weather_synced = self.weather_engine.sync_corridor_weather(run_date, limit=train_limit or 10)
        print(f"[INFO] Synced weather for {weather_synced} stations.")

        # 2. Get trains to poll
        with self.db.transaction() as cur:
            query = "SELECT train_no FROM trains ORDER BY priority ASC"
            if train_limit:
                query += f" LIMIT {train_limit}"
            cur.execute(query)
            train_rows = cur.fetchall()

        train_nos = [r["train_no"] for r in train_rows]
        print(f"[INFO] Polling running status for {len(train_nos)} trains...")

        total_upserted = 0
        total_quarantined = 0
        adapter_usage = {}

        all_valid_events: List[StationEvent] = []

        for t_no in train_nos:
            raw_events, source_used = self.fetch_with_failover(t_no, run_date)
            adapter_usage[source_used] = adapter_usage.get(source_used, 0) + 1

            # Quality gate filtering
            report = self.quality_gate.validate_events(raw_events)
            total_quarantined += report.quarantined_count
            all_valid_events.extend(report.passed_events)

        # 3. Idempotent batch upsert into station_events
        with self.db.transaction() as cur:
            cur.executemany(
                """
                INSERT OR REPLACE INTO station_events (
                    train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep,
                    delay_arr_min, delay_dep_min, collected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [ev.to_tuple() for ev in all_valid_events],
            )
            total_upserted = len(all_valid_events)

        print(f"[SUCCESS] Collection cycle complete: {total_upserted} events upserted, {total_quarantined} quarantined.")
        return {
            "date": date_str,
            "trains_polled": len(train_nos),
            "events_upserted": total_upserted,
            "events_quarantined": total_quarantined,
            "adapter_breakdown": adapter_usage,
        }


def run_cron():
    """Entrypoint for scheduled GitHub Actions / cron worker."""
    collector = DataCollector()
    summary = collector.run_collection_cycle()
    print("=== Collector Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    run_cron()
