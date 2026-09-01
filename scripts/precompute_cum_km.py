"""Precomputes cumulative kilometer distances for each train route station (Phase B6).

Stores the computed distances in the `route_cum_km` table for O(1) distance lookups
and linear position interpolation.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import Database, get_db


def precompute_cumulative_km(db: Optional[Database] = None) -> int:
    """Populates route_cum_km from route_stations and section distances."""
    db_inst = db or get_db()
    with db_inst.transaction() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS route_cum_km (
                train_no TEXT NOT NULL,
                station_code TEXT NOT NULL,
                seq INTEGER NOT NULL,
                cum_km REAL NOT NULL,
                PRIMARY KEY (train_no, seq)
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_route_cum_km_lookup ON route_cum_km(train_no, station_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_route_cum_km_seq ON route_cum_km(train_no, seq);")

        # Populate from route_stations
        cur.execute("DELETE FROM route_cum_km;")
        cur.execute(
            """
            INSERT OR REPLACE INTO route_cum_km (train_no, station_code, seq, cum_km)
            SELECT train_no, station_code, seq, COALESCE(distance_km, 0.0) as cum_km
            FROM route_stations
            ORDER BY train_no, seq;
            """
        )
        cur.execute("SELECT COUNT(*) FROM route_cum_km;")
        total_rows = cur.fetchone()[0]

    print(f"[SUCCESS] Populated `route_cum_km` with {total_rows:,} station coordinates.")
    return total_rows


if __name__ == "__main__":
    precompute_cumulative_km()
