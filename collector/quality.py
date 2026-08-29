"""RailTwin-X Data Quality Gates & Anomaly Quarantine Engine.

Rejects corrupted, non-monotonic, or extreme outlier data rows before insertion
into the station_events table.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Tuple

from config import settings
from collector.adapters.base import StationEvent


@dataclass
class QualityGateReport:
    """Detailed summary of quality gate evaluation."""

    total_events: int
    passed_events: List[StationEvent]
    quarantined_events: List[Tuple[StationEvent, str]]  # (event, rejection_reason)

    @property
    def passed_count(self) -> int:
        return len(self.passed_events)

    @property
    def quarantined_count(self) -> int:
        return len(self.quarantined_events)


class QualityGate:
    """Evaluates incoming StationEvents against 4 strict validation rules."""

    def __init__(
        self,
        max_delay_min: int = settings.MAX_SANITY_DELAY_MINUTES,
        min_delay_min: int = settings.MIN_SANITY_DELAY_MINUTES,
        stale_hours: int = settings.STALE_EVENT_THRESHOLD_HOURS,
    ):
        self.max_delay_min = max_delay_min
        self.min_delay_min = min_delay_min
        self.stale_hours = stale_hours

    def validate_events(self, events: List[StationEvent]) -> QualityGateReport:
        """Validates a list of events for a single train run, checking sanity & monotonicity."""
        if not events:
            return QualityGateReport(total_events=0, passed_events=[], quarantined_events=[])

        passed: List[StationEvent] = []
        quarantined: List[Tuple[StationEvent, str]] = []

        # Sort by sequence to check monotonicity
        sorted_events = sorted(events, key=lambda e: e.seq)

        for i, ev in enumerate(sorted_events):
            # 1. Sanity Gate: Outlier delay check
            if ev.delay_arr_min > self.max_delay_min or ev.delay_arr_min < self.min_delay_min:
                quarantined.append((ev, f"Delay {ev.delay_arr_min}m outside sanity bounds [{self.min_delay_min}, {self.max_delay_min}]"))
                continue

            if ev.delay_dep_min > self.max_delay_min or ev.delay_dep_min < self.min_delay_min:
                quarantined.append((ev, f"Dep delay {ev.delay_dep_min}m outside sanity bounds [{self.min_delay_min}, {self.max_delay_min}]"))
                continue

            # 2. Completeness Gate: Essential fields must exist
            if not ev.train_no or not ev.station_code or not ev.run_date:
                quarantined.append((ev, "Missing required primary identity fields (train_no/station_code/run_date)"))
                continue

            # 3. Monotonicity Gate: Actual time progression along journey
            if i > 0 and len(passed) > 0:
                prev = passed[-1]
                if prev.actual_dep and ev.actual_arr:
                    prev_h, prev_m = [int(x) for x in prev.actual_dep.split(":")]
                    curr_h, curr_m = [int(x) for x in ev.actual_arr.split(":")]
                    prev_minutes = prev_h * 60 + prev_m
                    curr_minutes = curr_h * 60 + curr_m

                    # Handle overnight journey wrap (if diff < -12h, crossed midnight)
                    if curr_minutes < prev_minutes and (prev_minutes - curr_minutes) < 720:
                        quarantined.append((ev, f"Non-monotonic actual time: {ev.actual_arr} is earlier than previous {prev.actual_dep}"))
                        continue

            passed.append(ev)

        return QualityGateReport(
            total_events=len(events),
            passed_events=passed,
            quarantined_events=quarantined,
        )


if __name__ == "__main__":
    import datetime
    print("=== Quality Gate Demo ===")
    gate = QualityGate()
    t_today = datetime.date.today().isoformat()
    test_events = [
        StationEvent("TRAIN_01", t_today, 1, "STN_A", "06:00", "06:05", "06:05", "06:10", 5, 5, f"{t_today}T06:00:00+05:30"),
        StationEvent("TRAIN_01", t_today, 2, "STN_B", "08:30", "08:35", "08:37", "08:40", 5, 3, f"{t_today}T08:30:00+05:30"),
        StationEvent("TRAIN_01", t_today, 3, "STN_C", "10:30", "22:00", "10:30", "22:00", 690, 690, f"{t_today}T10:30:00+05:30"), # Should be quarantined
    ]
    report = gate.validate_events(test_events)
    print(f"Total: {report.total_events}, Passed: {report.passed_count}, Quarantined: {report.quarantined_count}")
    for ev, reason in report.quarantined_events:
        print(f"  [QUARANTINED] Train {ev.train_no} @ {ev.station_code}: {reason}")
