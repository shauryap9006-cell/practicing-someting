"""RailTwin-X TimeProvider Architecture.

Provides an injectable clock abstraction so that all modules (collector, ML,
simulator, ops, API) can operate either in live wall-clock time (RealClock)
or in a fully deterministic replay/simulation environment (ReplayClock).

All timestamps are in Indian Standard Time (IST, UTC+05:30).
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import Optional

IST_TIMEZONE = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")


class TimeProvider(ABC):
    """Abstract interface for system time provider."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Returns 'live' or 'replay'."""
        pass

    @abstractmethod
    def now(self) -> datetime.datetime:
        """Returns the current datetime in IST."""
        pass

    def now_iso(self) -> str:
        """Returns current time formatted as ISO 8601 string in IST."""
        return self.now().isoformat()

    def today_str(self) -> str:
        """Returns current date formatted as YYYY-MM-DD."""
        return self.now().strftime("%Y-%m-%d")

    def parse_time(self, time_str: str) -> datetime.datetime:
        """Parses an ISO string or HH:MM string into datetime in IST."""
        if "T" in time_str:
            dt = datetime.datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=IST_TIMEZONE)
            return dt.astimezone(IST_TIMEZONE)
        elif ":" in time_str:
            # Assume HH:MM for today's date
            parts = [int(p) for p in time_str.split(":")]
            curr = self.now()
            return datetime.datetime(
                curr.year, curr.month, curr.day, parts[0], parts[1], tzinfo=IST_TIMEZONE
            )
        else:
            raise ValueError(f"Unrecognized time format: {time_str}")


class RealClock(TimeProvider):
    """Real-time clock reading host system time in IST."""

    @property
    def mode(self) -> str:
        return "live"

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=IST_TIMEZONE)


class ReplayClock(TimeProvider):
    """Deterministic replay clock with manual or automated time progression."""

    def __init__(self, start_time: Optional[datetime.datetime | str] = None):
        if start_time is None:
            self._current_time = datetime.datetime.now(tz=IST_TIMEZONE)
        elif isinstance(start_time, str):
            if "T" in start_time:
                dt = datetime.datetime.fromisoformat(start_time)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=IST_TIMEZONE)
                self._current_time = dt.astimezone(IST_TIMEZONE)
            else:
                # Format YYYY-MM-DD HH:MM
                parts = start_time.split(" ")
                y, m, d = [int(x) for x in parts[0].split("-")]
                hh, mm = [int(x) for x in parts[1].split(":")]
                self._current_time = datetime.datetime(y, m, d, hh, mm, tzinfo=IST_TIMEZONE)
        else:
            if start_time.tzinfo is None:
                self._current_time = start_time.replace(tzinfo=IST_TIMEZONE)
            else:
                self._current_time = start_time.astimezone(IST_TIMEZONE)

    @property
    def mode(self) -> str:
        return "replay"

    def now(self) -> datetime.datetime:
        return self._current_time

    def set_time(self, new_time: datetime.datetime | str) -> None:
        """Sets the replay clock to an explicit datetime."""
        if isinstance(new_time, str):
            self._current_time = self.parse_time(new_time)
        else:
            if new_time.tzinfo is None:
                self._current_time = new_time.replace(tzinfo=IST_TIMEZONE)
            else:
                self._current_time = new_time.astimezone(IST_TIMEZONE)

    def advance(self, minutes: float = 1.0) -> datetime.datetime:
        """Advances the replay clock by a given number of minutes."""
        self._current_time += datetime.timedelta(minutes=minutes)
        return self._current_time


# Default system clock singleton
GLOBAL_CLOCK: TimeProvider = RealClock()


def get_clock() -> TimeProvider:
    """Returns the active global clock instance."""
    return GLOBAL_CLOCK


def set_global_clock(clock: TimeProvider) -> None:
    """Sets the active global clock instance."""
    global GLOBAL_CLOCK
    GLOBAL_CLOCK = clock


if __name__ == "__main__":
    print("=== RailTwin-X TimeProvider Demo ===")
    real = RealClock()
    print(f"RealClock (mode: {real.mode}): now = {real.now_iso()}, today = {real.today_str()}")

    replay = ReplayClock(real.now())
    print(f"ReplayClock (mode: {replay.mode}): now = {replay.now_iso()}")
    replay.advance(45.5)
    print(f"ReplayClock after +45.5 min: now = {replay.now_iso()}")
