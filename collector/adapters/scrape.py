"""RailTwin-X Adapter B: Direct Web Scraper Source.

Scrapes public railway running status portals (erail / IndiaRailInfo / NTES patterns) directly
with polite rate limiting and regex-based HTML/JSON extraction.
"""

from __future__ import annotations

import datetime
import re
import time
from typing import List, Optional
import requests

from config import settings
from collector.adapters.base import LiveSource, StationEvent
from engine.clocks import get_clock


class ScrapeSource(LiveSource):
    """Direct web scraping source adapter supporting eRail and IndiaRailInfo formats."""

    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT_SECONDS
        self.delay = settings.POLITE_SCRAPE_DELAY_SECONDS
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
        })

    @property
    def source_name(self) -> str:
        return "WebScrape"

    def fetch_running_status(
        self, train_no: str, run_date: datetime.date
    ) -> list[StationEvent]:
        """Scrapes and parses running status from public railway status portals."""
        # Polite rate limiting
        time.sleep(self.delay)

        # Scrape attempt URL (erail / public query endpoint)
        url = f"https://erail.in/data.aspx?Action=TRAINLIVE&TrainNo={train_no}&Date={run_date.strftime('%d-%b-%Y')}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200 and resp.text.strip() and "INVALID" not in resp.text.upper() and len(resp.text) >= 50:
                return self._parse_erail_raw_response(train_no, run_date, resp.text)
        except Exception:
            pass

        # Fallback to secondary scrape target (e.g. IndiaRailInfo pattern or public json mirror)
        try:
            iri_url = f"https://indiarailinfo.com/train/{train_no}/history"
            resp = self.session.get(iri_url, timeout=self.timeout)
            if resp.status_code == 200 and len(resp.text) > 100:
                events = self._parse_indiarailinfo_html(train_no, run_date, resp.text)
                if events:
                    return events
        except Exception:
            pass

        raise RuntimeError(f"Scrape adapter failed for {train_no} across all scraper targets")

    def _parse_erail_raw_response(
        self, train_no: str, run_date: datetime.date, raw_text: str
    ) -> list[StationEvent]:
        """Parses erail tilde/caret-separated data stream into StationEvent objects."""
        events = []
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
    ) -> list[StationEvent]:
        """Extracts tabular station events from IndiaRailInfo history HTML tables."""
        events = []
        clock = get_clock()
        collected_at = clock.now_iso()
        date_str = run_date.strftime("%Y-%m-%d")

        # Regex match for station table rows: code, arr, dep, delay
        pattern = re.compile(r'<tr[^>]*>.*?<td[^>]*>([A-Z0-9]{2,6})</td>.*?<td[^>]*>(\d{2}:\d{2}|--)</td>.*?<td[^>]*>(\d{2}:\d{2}|--)</td>.*?<td[^>]*>(-?\d+)\s*m?</td>', re.DOTALL | re.IGNORECASE)
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
    print("=== Scraper Adapter Demo ===")
    src = ScrapeSource()
    print(f"Source: {src.source_name}, Ready to scrape with polite delay = {src.delay}s")

