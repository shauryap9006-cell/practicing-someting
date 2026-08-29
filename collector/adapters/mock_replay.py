"""RailTwin-X Adapter C: Offline Deterministic Replay Source.

Generates realistic, physically consistent running status events directly from
the database route definitions and historical lateness distributions when external APIs
are unreachable.
"""

from __future__ import annotations

import datetime
import math
import random
from typing import Optional

from collector.adapters.base import LiveSource, StationEvent
from data.db import Database, get_db
from engine.clocks import get_clock


class MockReplaySource(LiveSource):
    """Offline deterministic replay/synthetic data source."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    @property
    def source_name(self) -> str:
        return "MockReplay"

    def fetch_running_status(
        self, train_no: str, run_date: datetime.date
    ) -> list[StationEvent]:
        """Generates consistent StationEvents from timetable route and realistic delays."""
        clock = get_clock()
        collected_at = clock.now_iso()
        date_str = run_date.strftime("%Y-%m-%d")

        with self.db.transaction() as cur:
            cur.execute("SELECT priority FROM trains WHERE train_no = ?", (train_no,))
            train_row = cur.fetchone()
            priority = train_row["priority"] if train_row else 2

            cur.execute(
                """
                SELECT seq, station_code, sched_arr, sched_dep, halt_min, distance_km
                FROM route_stations
                WHERE train_no = ?
                ORDER BY seq
                """,
                (train_no,),
            )
            route = cur.fetchall()

        if not route:
            raise ValueError(f"Train {train_no} route not found in database.")

        # Deterministic lateness based on train and date hash
        seed_val = hash(f"{train_no}_{date_str}")
        rng = random.Random(seed_val)

        chronic_bias = (abs(hash(train_no)) % 20) - 5
        curr_delay = max(0, int(rng.gauss(chronic_bias, 10 if priority > 1 else 5)))

        events = []
        for r in route:
            seq = r["seq"]
            stn = r["station_code"]
            sched_arr = r["sched_arr"]
            sched_dep = r["sched_dep"]

            # Small section delta
            delta = rng.choice([-3, -1, 0, 0, 1, 4, 10]) if priority > 1 else rng.choice([-2, 0, 0, 1, 3])
            curr_delay = max(0, curr_delay + delta)

            actual_arr = None
            if sched_arr:
                sh, sm = [int(x) for x in sched_arr.split(":")]
                act_arr_dt = datetime.datetime(run_date.year, run_date.month, run_date.day, sh, sm) + datetime.timedelta(minutes=curr_delay)
                actual_arr = act_arr_dt.strftime("%H:%M")

            delay_arr = curr_delay

            # Dwell
            dwell_extra = rng.randint(0, 3) if rng.random() < 0.25 else 0
            curr_delay += dwell_extra

            actual_dep = None
            if sched_dep:
                sh, sm = [int(x) for x in sched_dep.split(":")]
                act_dep_dt = datetime.datetime(run_date.year, run_date.month, run_date.day, sh, sm) + datetime.timedelta(minutes=curr_delay)
                actual_dep = act_dep_dt.strftime("%H:%M")

            delay_dep = curr_delay

            events.append(
                StationEvent(
                    train_no=train_no,
                    run_date=date_str,
                    seq=seq,
                    station_code=stn,
                    sched_arr=sched_arr,
                    actual_arr=actual_arr,
                    sched_dep=sched_dep,
                    actual_dep=actual_dep,
                    delay_arr_min=delay_arr,
                    delay_dep_min=delay_dep,
                    collected_at=collected_at,
                )
            )

        return events


if __name__ == "__main__":
    print("=== Mock Replay Adapter Demo ===")
    src = MockReplaySource()
    with src.db.transaction() as cur:
        cur.execute("SELECT train_no FROM trains LIMIT 1")
        tr_row = cur.fetchone()
    t_sample = tr_row["train_no"] if tr_row else "10001"
    events = src.fetch_running_status(t_sample, datetime.date.today())
    print(f"Generated {len(events)} events for train {t_sample}. First stop delay: {events[0].delay_arr_min if events else 0}m")


