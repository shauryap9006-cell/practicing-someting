"""RailTwin-X Adapter B: Direct Web Scraper Source.

Scrapes public railway running status portals (erail / IndiaRailInfo / NTES patterns) directly
with polite rate limiting, explicit connect/read timeouts, exponential backoff with jitter,
small sleep slices, and robust response validation.
"""

from __future__ import annotations

import datetime
import logging
import random
import re
import time
from typing import List, Optional, Tuple

import requests

from collector.adapters.base import LiveSource, StationEvent
from config import settings
from engine.clocks import get_clock

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT: float = 5.0
READ_TIMEOUT: float = 15.0
DEFAULT_TIMEOUT: Tuple[float, float] = (CONNECT_TIMEOUT, READ_TIMEOUT)
MAX_RETRIES: int = 3
SLEEP_SLICE_SECONDS: float = 0.1


def _interruptible_sleep(duration: float, step: float = SLEEP_SLICE_SECONDS) -> None:
    """Sleeps in small increments to prevent stalling threads and allow responsive interruption."""
    remaining = max(0.0, duration)
    while remaining > 0:
        sleep_time = min(step, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time


class ScrapeSource(LiveSource):
    """Direct web scraping source adapter supporting eRail and IndiaRailInfo formats."""

    def __init__(
        self,
        timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        polite_delay: Optional[float] = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = (
            polite_delay
            if polite_delay is not None
            else getattr(settings, "POLITE_SCRAPE_DELAY_SECONDS", 2.0)
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/html, */*",
            }
        )

    @property
    def source_name(self) -> str:
        return "WebScrape"

    def _polite_sleep(self) -> None:
        """Applies polite delay with jitter (delay ± 0.5s) in small sleep slices."""
        jitter = random.uniform(-0.5, 0.5)
        delay = max(0.1, self.delay + jitter)
        _interruptible_sleep(delay)

    def _retry_backoff(self, attempt: int) -> None:
        """Applies exponential backoff with jitter for retries in small sleep slices."""
        backoff = (1.0 * (2**attempt)) + random.uniform(0.0, 0.5)
        _interruptible_sleep(backoff)

    def _scrape_erail(self, train_no: str, run_date: datetime.date) -> Optional[List[StationEvent]]:
        """Attempts scraping live status from eRail with backoff and response validation."""
        url = (
            f"https://erail.in/data.aspx?Action=TRAINLIVE&TrainNo={train_no}"
            f"&Date={run_date.strftime('%d-%b-%Y')}"
        )
        for attempt in range(self.max_retries):
            if attempt > 0:
                self._retry_backoff(attempt)
            else:
                self._polite_sleep()

            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(
                        "eRail HTTP %d for train %s (attempt %d/%d)",
                        resp.status_code,
                        train_no,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue

                raw_text = resp.text.strip() if resp.text else ""
                if not raw_text or "INVALID" in raw_text.upper() or len(raw_text) < 50:
                    logger.warning(
                        "eRail invalid/empty payload for train %s (attempt %d/%d)",
                        train_no,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue

                events = self._parse_erail_raw_response(train_no, run_date, raw_text)
                if events:
                    return events
            except Exception as exc:
                logger.warning(
                    "eRail request/parse error for train %s (attempt %d/%d): %s",
                    train_no,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

        return None

    def _scrape_indiarailinfo(
        self, train_no: str, run_date: datetime.date
    ) -> Optional[List[StationEvent]]:
        """Attempts scraping running status from IndiaRailInfo with backoff and validation."""
        iri_url = f"https://indiarailinfo.com/train/{train_no}/history"
        for attempt in range(self.max_retries):
            if attempt > 0:
                self._retry_backoff(attempt)
            else:
                self._polite_sleep()

            try:
                resp = self.session.get(iri_url, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(
                        "IndiaRailInfo HTTP %d for train %s (attempt %d/%d)",
                        resp.status_code,
                        train_no,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue

                raw_text = resp.text.strip() if resp.text else ""
                if not raw_text or len(raw_text) <= 100:
                    logger.warning(
                        "IndiaRailInfo invalid/empty payload for train %s (attempt %d/%d)",
                        train_no,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue

                events = self._parse_indiarailinfo_html(train_no, run_date, raw_text)
                if events:
                    return events
            except Exception as exc:
                logger.warning(
                    "IndiaRailInfo request/parse error for train %s (attempt %d/%d): %s",
                    train_no,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

        return None

    def fetch_running_status(self, train_no: str, run_date: datetime.date) -> List[StationEvent]:
        """Scrapes and parses running status from public railway status portals.

        Performs per-target try/except with polite rate limiting, explicit timeouts,
        exponential backoff + jitter, and robust response validation.
        Malformed or failed responses log warnings and skip the cycle without raising.
        """
        # Target 1: eRail
        try:
            events = self._scrape_erail(train_no, run_date)
            if events:
                return events
        except Exception as exc:
            logger.warning("Unexpected error during eRail scrape for train %s: %s", train_no, exc)

        # Target 2: IndiaRailInfo
        try:
            events = self._scrape_indiarailinfo(train_no, run_date)
            if events:
                return events
        except Exception as exc:
            logger.warning(
                "Unexpected error during IndiaRailInfo scrape for train %s: %s", train_no, exc
            )

        logger.warning(
            "Scrape adapter failed for train %s across all scraper targets; skipping cycle",
            train_no,
        )
        return []

    def _parse_erail_raw_response(
        self, train_no: str, run_date: datetime.date, raw_text: str
    ) -> List[StationEvent]:
        """Parses erail tilde/caret-separated data stream into StationEvent objects."""
        events: List[StationEvent] = []
        clock = get_clock()
        collected_at = clock.now_iso()
        date_str = run_date.strftime("%Y-%m-%d")

        # Erail formats lines as station rows separated by tilde (~) or caret (^)
        rows = raw_text.split("~")
        for idx, row in enumerate(rows, start=1):
            parts = row.split("^")
            if len(parts) < 4:
                continue

            stn_code = parts[0].strip().upper()
            sched_arr = parts[1].strip() if len(parts) > 1 and ":" in parts[1] else None
            actual_arr = parts[2].strip() if len(parts) > 2 and ":" in parts[2] else sched_arr
            sched_dep = parts[3].strip() if len(parts) > 3 and ":" in parts[3] else None
            actual_dep = parts[4].strip() if len(parts) > 4 and ":" in parts[4] else sched_dep

            # Extract delay minutes
            delay_arr = 0
            if len(parts) > 5 and parts[5].replace("-", "").isdigit():
                delay_arr = int(parts[5])

            delay_dep = delay_arr

            events.append(
                StationEvent(
                    train_no=train_no,
                    run_date=date_str,
                    seq=idx,
                    station_code=stn_code,
                    sched_arr=sched_arr,
                    actual_arr=actual_arr,
                    sched_dep=sched_dep,
                    actual_dep=actual_dep,
                    delay_arr_min=delay_arr,
                    delay_dep_min=delay_dep,
                    collected_at=collected_at,
                )
            )

        if not events:
            raise ValueError(f"Parsed 0 station events from raw scrape text for {train_no}")

        return events

    def _parse_indiarailinfo_html(
        self, train_no: str, run_date: datetime.date, html: str
    ) -> List[StationEvent]:
        """Extracts tabular station events from IndiaRailInfo history HTML tables."""
        events: List[StationEvent] = []
        clock = get_clock()
        collected_at = clock.now_iso()
        date_str = run_date.strftime("%Y-%m-%d")

        # Regex match for station table rows: code, arr, dep, delay
        pattern = re.compile(
            r"<tr[^>]*>.*?<td[^>]*>([A-Z0-9]{2,6})</td>.*?<td[^>]*>(\d{2}:\d{2}|--)</td>.*?<td[^>]*>(\d{2}:\d{2}|--)</td>.*?<td[^>]*>(-?\d+)\s*m?</td>",
            re.DOTALL | re.IGNORECASE,
        )
        matches = pattern.findall(html)
        for idx, (stn, arr, dep, delay_str) in enumerate(matches, start=1):
            sched_arr = arr if arr != "--" else None
            sched_dep = dep if dep != "--" else None
            delay = int(delay_str) if delay_str.lstrip("-").isdigit() else 0

            events.append(
                StationEvent(
                    train_no=train_no,
                    run_date=date_str,
                    seq=idx,
                    station_code=stn.upper(),
                    sched_arr=sched_arr,
                    actual_arr=sched_arr,
                    sched_dep=sched_dep,
                    actual_dep=sched_dep,
                    delay_arr_min=delay,
                    delay_dep_min=delay,
                    collected_at=collected_at,
                )
            )
        return events


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Scraper Adapter Demo ===")
    src = ScrapeSource()
    print(f"Source: {src.source_name}, timeout={src.timeout}, polite delay={src.delay}s")
