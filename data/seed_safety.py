"""Development bootstrap data for safety modules (level crossings).

These rows exist only so an empty development database renders the Level
Crossing board. They are never inserted in production, carry no fabricated
contact numbers, and use the current clock for inspection timestamps.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Tuple

from config import settings


def _sample_level_crossings(now_iso: str) -> List[Tuple]:
    station = settings.DEFAULT_STATION_CODE.upper()
    return [
        ("LC-102", station, 2.4, "MANNED_INTERLOCKED", "NORMAL", now_iso, "Unassigned", ""),
        ("LC-105", station, 5.8, "MANNED_INTERLOCKED", "NORMAL", now_iso, "Unassigned", ""),
        ("LC-118", station, 18.2, "SPECIAL_CLASS", "NORMAL", now_iso, "Unassigned", ""),
        ("LC-124", station, 45.1, "MANNED_NON_INTERLOCKED", "DEFECTIVE", now_iso, "Unassigned", ""),
    ]


def bootstrap_level_crossings_if_empty(cur: sqlite3.Cursor) -> int:
    """Inserts sample level crossings when the table is empty (non-production only)."""
    if settings.ENV.strip().lower() == "production":
        return 0
    cur.execute("SELECT COUNT(*) AS count FROM level_crossings;")
    if int(cur.fetchone()["count"]) > 0:
        return 0
    rows = _sample_level_crossings(datetime.now(timezone.utc).isoformat())
    cur.executemany(
        """
        INSERT INTO level_crossings (
            lc_number, station_code, km, gate_type, status,
            last_inspected, gateman_name, contact_phone
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    return len(rows)
