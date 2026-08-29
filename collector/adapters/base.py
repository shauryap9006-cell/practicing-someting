"""RailTwin-X Base Live Data Source Adapter Interface.

Defines the normalized StationEvent data model and the abstract LiveSource interface
adhering to the Adapter pattern.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class StationEvent:
    """Normalized train station event across all live status data sources."""

    train_no: str
    run_date: str  # YYYY-MM-DD
    seq: int
    station_code: str
    sched_arr: Optional[str] = None  # HH:MM or None
    actual_arr: Optional[str] = None  # HH:MM or None
    sched_dep: Optional[str] = None  # HH:MM or None
    actual_dep: Optional[str] = None  # HH:MM or None
    delay_arr_min: int = 0
    delay_dep_min: int = 0
    collected_at: str = ""  # ISO 8601 string in IST

    def to_tuple(self) -> tuple:
        """Returns tuple suitable for SQLite station_events insertion."""
        return (
            self.train_no,
            self.run_date,
            self.seq,
            self.station_code,
            self.sched_arr,
            self.actual_arr,
            self.sched_dep,
            self.actual_dep,
            self.delay_arr_min,
            self.delay_dep_min,
            self.collected_at,
        )


class LiveSource(ABC):
    """Abstract interface for train status data providers."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable identifier for the source adapter."""
        pass

    @abstractmethod
    def fetch_running_status(
        self, train_no: str, run_date: datetime.date
    ) -> list[StationEvent]:
        """Fetches and parses live running status into normalized StationEvents.

        Raises:
            Exception: If source is unreachable, times out, or returns invalid payload.
        """
        pass
