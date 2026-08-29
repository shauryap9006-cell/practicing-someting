"""RailTwin-X Adapter A: RapidAPI Live Status Source with Round-Robin Rotation.

Connects to RapidAPI Indian Railways endpoints, normalizes raw payloads,
supports multiple API keys in round-robin rotation to avoid rate limits,
and converts responses into standard StationEvent objects.
"""

from __future__ import annotations

import datetime
import itertools
from typing import List, Optional
import requests

from config import settings
from collector.adapters.base import LiveSource, StationEvent
from engine.clocks import get_clock


class RapidAPISource(LiveSource):
    """Adapter for RapidAPI Indian Railways Live Running Status with Round-Robin Keys."""

    def __init__(self, api_keys: Optional[List[str] | str] = None):
        raw_keys = api_keys or settings.RAPIDAPI_KEY
        if isinstance(raw_keys, str):
            # Supports comma-separated keys in settings/env: KEY1,KEY2,KEY3
            self.keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        else:
            self.keys = list(raw_keys) if raw_keys else []

        self._key_cycle = itertools.cycle(self.keys) if self.keys else None
        self.host = settings.RAPIDAPI_HOST
        self.base_url = settings.RAPIDAPI_BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT_SECONDS

    @property
    def source_name(self) -> str:
        return "RapidAPI"

    @property
    def api_key(self) -> Optional[str]:
        """Returns the primary or current active API key."""
        return self.keys[0] if self.keys else None

    def _get_next_key(self) -> str:
        """Cycles to next available API key in the pool."""
        if not self._key_cycle:
            raise ValueError("RapidAPI key not configured in settings/environment.")
        return next(self._key_cycle)

    def fetch_running_status(
        self, train_no: str, run_date: datetime.date
    ) -> list[StationEvent]:
        """Queries RapidAPI live train status endpoint with multi-key failover."""
        if not self.keys:
            raise ValueError("No RapidAPI keys configured in settings/environment.")

        last_error = None
        # Try each key in rotation once if rate limited or failed
        for _ in range(len(self.keys)):
            current_key = self._get_next_key()
            try:
                return self._query_with_key(current_key, train_no, run_date)
            except requests.HTTPError as http_err:
                if http_err.response is not None and http_err.response.status_code in (429, 403, 401):
                    # Rate limit or auth error on this key: rotate to next key
                    last_error = http_err
                    continue
                raise
            except Exception as err:
                last_error = err
                continue

        raise RuntimeError(f"RapidAPI failed across all {len(self.keys)} keys: {last_error}")

    def _query_with_key(self, key: str, train_no: str, run_date: datetime.date) -> list[StationEvent]:
        url = f"{self.base_url}/trains/{train_no}/live"
        headers = {
            "X-RapidAPI-Key": key,
            "X-RapidAPI-Host": self.host,
        }
        params = {"date": run_date.strftime("%Y-%m-%d")}

        response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        events = []
        clock = get_clock()
        collected_at = clock.now_iso()
        date_str = run_date.strftime("%Y-%m-%d")

        stations = data.get("stations", []) or data.get("data", {}).get("stations", [])
        for idx, item in enumerate(stations, start=1):
            stn_code = item.get("station_code") or item.get("code") or ""
            if not stn_code:
                continue

            events.append(
                StationEvent(
                    train_no=train_no,
                    run_date=date_str,
                    seq=item.get("seq", idx),
                    station_code=stn_code.upper().strip(),
                    sched_arr=item.get("sched_arr") or item.get("sch_arr"),
                    actual_arr=item.get("actual_arr") or item.get("act_arr"),
                    sched_dep=item.get("sched_dep") or item.get("sch_dep"),
                    actual_dep=item.get("actual_dep") or item.get("act_dep"),
                    delay_arr_min=int(item.get("delay_arr", 0) or item.get("delay_arr_min", 0)),
                    delay_dep_min=int(item.get("delay_dep", 0) or item.get("delay_dep_min", 0)),
                    collected_at=collected_at,
                )
            )

        return events


if __name__ == "__main__":
    print("=== RapidAPI Adapter Demo ===")
    src = RapidAPISource()
    print(f"Source: {src.source_name}, Total Keys Loaded: {len(src.keys)}")

