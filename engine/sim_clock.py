"""engine/sim_clock.py — Virtual IST Clock for RailTwin-X Digital Twin (F02, F28).

Implements TimeProvider interface with virtual time, acceleration factor (1x to 60x),
and dynamic "auto" start time detection (hour of maximum concurrent active corridor trains).
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

from config import settings
from data.db import Database, get_db
from engine.clocks import IST_TIMEZONE, TimeProvider


def find_peak_corridor_hour(db: Optional[Database] = None) -> int:
    """Scans timetable to find the hour (0..23) with maximum concurrent active corridor trains."""
    db_inst = db or get_db()
    try:
        with db_inst.transaction() as cur:
            cur.execute(
                """
                SELECT train_no, MIN(sched_dep) as t_dep, MAX(sched_arr) as t_arr
                FROM route_stations
                GROUP BY train_no;
                """
            )
            rows = cur.fetchall()

        hour_counts = [0] * 24
        for r in rows:
            dep = r["t_dep"]
            arr = r["t_arr"]
            if dep and arr and ":" in str(dep) and ":" in str(arr):
                try:
                    h_dep = int(str(dep).split(":")[0])
                    h_arr = int(str(arr).split(":")[0])
                    if h_dep <= h_arr:
                        for h in range(h_dep, h_arr + 1):
                            hour_counts[h % 24] += 1
                    else:
                        for h in range(h_dep, 24):
                            hour_counts[h] += 1
                        for h in range(0, h_arr + 1):
                            hour_counts[h] += 1
                except Exception:
                    pass

        return int(max(range(24), key=lambda h: hour_counts[h]))
    except Exception:
        return 11  # Robust default peak corridor hour


class SimulatedClock(TimeProvider):
    """Virtual IST clock supporting acceleration, jumps, and timetable synchronization."""

    def __init__(
        self,
        start_time: Optional[str | datetime.datetime] = None,
        accel: float = 1.0,
        db: Optional[Database] = None,
    ):
        self.db = db or get_db()
        self._accel = max(0.1, min(60.0, float(accel)))
        self._real_base = datetime.datetime.now(tz=IST_TIMEZONE)

        # Determine start virtual time
        today = self._real_base.date()
        st = start_time if start_time is not None else settings.SIM_CLOCK_START
        if str(st).lower() == "auto":
            peak_hour = find_peak_corridor_hour(self.db)
            self._sim_base = datetime.datetime(
                today.year, today.month, today.day, peak_hour, 0, 0, tzinfo=IST_TIMEZONE
            )
        elif isinstance(st, str):
            if ":" in st and "T" not in st and len(st.split(":")) == 2:
                hh, mm = [int(x) for x in st.split(":")]
                self._sim_base = datetime.datetime(
                    today.year, today.month, today.day, hh, mm, 0, tzinfo=IST_TIMEZONE
                )
            else:
                self._sim_base = self.parse_time(st)
        elif isinstance(st, datetime.datetime):
            self._sim_base = st if st.tzinfo else st.replace(tzinfo=IST_TIMEZONE)
        else:
            self._sim_base = datetime.datetime(
                today.year, today.month, today.day, 11, 0, 0, tzinfo=IST_TIMEZONE
            )

    @property
    def mode(self) -> str:
        return "simulated"

    @property
    def accel(self) -> float:
        return self._accel

    def now(self) -> datetime.datetime:
        """Returns current virtual simulated time in IST."""
        real_now = datetime.datetime.now(tz=IST_TIMEZONE)
        real_elapsed_sec = (real_now - self._real_base).total_seconds()
        sim_elapsed_sec = real_elapsed_sec * self._accel
        return self._sim_base + datetime.timedelta(seconds=sim_elapsed_sec)

    def set_accel(self, factor: float) -> float:
        """Changes the acceleration factor without discontinuously jumping time."""
        current_sim_now = self.now()
        self._real_base = datetime.datetime.now(tz=IST_TIMEZONE)
        self._sim_base = current_sim_now
        self._accel = max(0.1, min(60.0, float(factor)))
        return self._accel

    def jump_to(self, target: str | datetime.datetime) -> datetime.datetime:
        """Jumps the simulated clock forward/backward to a specific target time."""
        if isinstance(target, str):
            if ":" in target and "T" not in target:
                hh, mm = [int(x) for x in target.split(":")[:2]]
                today = self.now().date()
                new_sim = datetime.datetime(
                    today.year, today.month, today.day, hh, mm, 0, tzinfo=IST_TIMEZONE
                )
            else:
                new_sim = self.parse_time(target)
        else:
            new_sim = target if target.tzinfo else target.replace(tzinfo=IST_TIMEZONE)

        self._real_base = datetime.datetime.now(tz=IST_TIMEZONE)
        self._sim_base = new_sim
        return self._sim_base

    def get_status(self) -> Dict[str, Any]:
        """Returns metadata status payload for /v1/meta/clock."""
        return {
            "sim_now": self.now_iso(),
            "real_now": datetime.datetime.now(tz=IST_TIMEZONE).isoformat(),
            "accel": self._accel,
            "mode": self.mode,
        }


_GLOBAL_SIM_CLOCK: Optional[SimulatedClock] = None


def get_sim_clock(
    db: Optional[Database] = None, start_time: Optional[str] = None, accel: Optional[float] = None
) -> SimulatedClock:
    """Returns singleton instance of SimulatedClock."""
    global _GLOBAL_SIM_CLOCK
    if _GLOBAL_SIM_CLOCK is None:
        init_accel = accel if accel is not None else settings.SIM_CLOCK_ACCEL
        _GLOBAL_SIM_CLOCK = SimulatedClock(start_time=start_time, accel=init_accel, db=db)
    return _GLOBAL_SIM_CLOCK
