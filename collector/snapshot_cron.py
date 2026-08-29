"""RailTwin-X Bucket C Live Snapshot Collector Cron (Module B1/ASSETS.md §2).

Captures continuous, timestamped train running snapshots across the corridor,
recording to SQLite `train_runs` and `run_snapshots` with explicit provenance tags
(rapidapi | synthetic | manual).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from collector.adapters.base import LiveSource, StationEvent
from collector.adapters.mock_replay import MockReplaySource
from collector.adapters.rapidapi import RapidAPISource
from collector.adapters.scrape import ScrapeSource
from data.db import Database, get_db
from engine.clocks import get_clock


def normalize_source_tag(source_name: str) -> str:
    """Ensures source matches the CHECK constraint: ('rapidapi', 'synthetic', 'manual')."""
    s = source_name.lower()
    if "rapidapi" in s:
        return "rapidapi"
    elif "manual" in s:
        return "manual"
    else:
        return "synthetic"


class SnapshotCollector:
    """Bucket C Telemetry Engine: collects and archives live running snapshots."""

    def __init__(self, db: Optional[Database] = None, adapters: Optional[List[LiveSource]] = None):
        self.db = db or get_db()
        self.adapters: List[LiveSource] = adapters if adapters is not None else [
            RapidAPISource(),
            ScrapeSource(),
            MockReplaySource(self.db),
        ]

    def fetch_train_status(self, train_no: str, run_date: datetime.date) -> tuple[List[StationEvent], str]:
        """Fetches train status through failover adapter chain with provenance tag."""
        for adapter in self.adapters:
            try:
                events = adapter.fetch_running_status(train_no, run_date)
                if events:
                    return events, normalize_source_tag(adapter.source_name)
            except Exception:
                continue

        mock_src = MockReplaySource(self.db)
        return mock_src.fetch_running_status(train_no, run_date), "synthetic"

    def record_snapshot_cycle(
        self,
        target_date: Optional[datetime.date] = None,
        train_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Executes a single snapshot cycle and appends to run_snapshots."""
        clock = get_clock()
        run_date = target_date or clock.now().date()
        date_str = run_date.strftime("%Y-%m-%d")
        now_iso = clock.now().isoformat()

        with self.db.transaction() as cur:
            query = "SELECT train_no FROM trains ORDER BY priority ASC"
            if train_limit:
                query += f" LIMIT {train_limit}"
            cur.execute(query)
            train_rows = cur.fetchall()

        train_nos = [r["train_no"] for r in train_rows]
        snapshots_recorded = 0
        runs_created = 0

        with self.db.transaction() as cur:
            for t_no in train_nos:
                events, source_tag = self.fetch_train_status(t_no, run_date)
                source_tag = normalize_source_tag(source_tag)
                if not events:
                    continue

                run_id = f"RUN-{t_no}-{date_str}"
                origin = events[0].station_code if events else "NDLS"
                dest = events[-1].station_code if events else "LKO"

                # Ensure train_runs entry exists
                cur.execute(
                    """
                    INSERT INTO train_runs (run_id, train_no, run_date, origin, dest, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO NOTHING;
                    """,
                    (run_id, t_no, date_str, origin, dest, source_tag, now_iso),
                )
                if cur.rowcount > 0:
                    runs_created += 1

                # Record snapshot for current / upcoming station
                current_event = events[len(events) // 2] if events else None
                if current_event:
                    cur.execute(
                        """
                        INSERT INTO run_snapshots (
                            run_id, ts, station_code, sch_arr, sch_dep, exp_arr, exp_dep,
                            delay_min, last_loc_station, lat, lng, raw_json, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            run_id,
                            now_iso,
                            current_event.station_code,
                            current_event.sched_arr,
                            current_event.sched_dep,
                            current_event.actual_arr,
                            current_event.actual_dep,
                            current_event.delay_arr_min,
                            current_event.station_code,
                            28.6139,
                            77.2090,
                            json.dumps(current_event.to_tuple()),
                            source_tag,
                        ),
                    )
                    snapshots_recorded += 1

        return {
            "run_date": date_str,
            "timestamp": now_iso,
            "trains_checked": len(train_nos),
            "runs_registered": runs_created,
            "snapshots_recorded": snapshots_recorded,
        }


def run_snapshot_cron():
    """CLI / Cron entrypoint for Bucket C snapshot capture."""
    collector = SnapshotCollector()
    summary = collector.record_snapshot_cycle()
    print("=== Bucket C Snapshot Cycle Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    run_snapshot_cron()
