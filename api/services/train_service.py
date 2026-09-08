"""Data access and service layer for train journeys and PNR tracking."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from data.db import Database


def get_train_info(db: Database, train_no: str) -> Optional[Dict[str, Any]]:
    """Fetches basic metadata for a train."""
    with db.transaction() as cur:
        cur.execute("SELECT name, class FROM trains WHERE train_no = ?", (train_no,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_train_route_stops(db: Database, train_no: str) -> List[Dict[str, Any]]:
    """Fetches ordered route stations for a train."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT rs.seq, rs.station_code, rs.sched_arr, rs.sched_dep, rs.distance_km, s.name as station_name
            FROM route_stations rs
            JOIN stations s ON rs.station_code = s.code
            WHERE rs.train_no = ?
            ORDER BY rs.seq
            """,
            (train_no,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_latest_station_event(db: Database, train_no: str) -> Optional[Dict[str, Any]]:
    """Fetches latest recorded station event for a train."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT seq, station_code, delay_arr_min, delay_dep_min
            FROM station_events
            WHERE train_no = ?
            ORDER BY run_date DESC, seq DESC LIMIT 1
            """,
            (train_no,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_pnr_candidate_trains(db: Database) -> List[Dict[str, Any]]:
    """Fetches top passenger trains with configured route stations for PNR demo mapping."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT t.train_no, t.name, t.class
            FROM trains t
            WHERE t.is_freight = 0 AND EXISTS (SELECT 1 FROM route_stations rs WHERE rs.train_no = t.train_no)
            ORDER BY t.priority ASC, t.train_no ASC
            LIMIT 5
            """
        )
        return [dict(r) for r in cur.fetchall()]


def get_pnr_route_stops(db: Database, train_no: str) -> List[Dict[str, Any]]:
    """Fetches ordered route stations for the PNR status display."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT rs.station_code, rs.seq, rs.sched_arr, rs.sched_dep, rs.distance_km, s.name AS station_name
            FROM route_stations rs JOIN stations s ON s.code = rs.station_code
            WHERE rs.train_no = ?
            ORDER BY rs.seq ASC
            """,
            (train_no,),
        )
        return [dict(r) for r in cur.fetchall()]
