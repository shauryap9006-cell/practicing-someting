"""RailTwin-X Open-Meteo Historical Weather Backfill Utility (ASSETS.md §1.3).

Backfills historical weather observations and fog flags across all corridor stations
using Open-Meteo Archive API, storing records in the `weather` table.
"""

from __future__ import annotations

import argparse
import datetime
from typing import Optional

from collector.weather import WeatherEngine
from data.db import Database, get_db


def backfill_corridor_weather(
    days_back: int = 30,
    end_date: Optional[datetime.date] = None,
    station_limit: Optional[int] = 10,
    db: Optional[Database] = None,
) -> dict:
    """Iterates backwards from end_date and syncs corridor weather."""
    database = db or get_db()
    engine = WeatherEngine(database)
    end = end_date or datetime.date.today()
    start = end - datetime.timedelta(days=days_back)

    print(f"[INFO] Starting weather backfill from {start} to {end} for top {station_limit} stations...")

    current_date = start
    total_records = 0
    days_processed = 0

    while current_date <= end:
        synced = engine.sync_corridor_weather(current_date, limit=station_limit)
        total_records += synced
        days_processed += 1
        current_date += datetime.timedelta(days=1)

    print(f"[SUCCESS] Backfilled {total_records} station-weather records across {days_processed} days.")
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days_processed": days_processed,
        "total_records_synced": total_records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historical weather data for RailTwin-X corridor.")
    parser.add_argument("--days", type=int, default=7, help="Number of historical days to backfill")
    parser.add_argument("--stations", type=int, default=5, help="Number of corridor stations to backfill")
    args = parser.parse_args()

    backfill_corridor_weather(days_back=args.days, station_limit=args.stations)
