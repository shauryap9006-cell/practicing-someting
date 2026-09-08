"""Data access and service layer for network state, simulation, and crew alerts."""

from __future__ import annotations

from typing import Any, Dict, List
from data.db import Database


def get_network_state_raw(db: Database) -> Dict[str, Any]:
    """Queries trains, route stations, latest station events, and active speed restrictions."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT train_no, name, class, priority
            FROM trains
            ORDER BY priority ASC, train_no ASC
            """
        )
        train_rows = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT train_no, seq, station_code, sched_arr, sched_dep
            FROM route_stations
            ORDER BY train_no, seq
            """
        )
        all_routes = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT se.train_no, se.seq, se.station_code, se.delay_arr_min, se.delay_dep_min
            FROM station_events se
            INNER JOIN (
                SELECT train_no, MAX(seq) as max_seq, MAX(run_date) as max_date
                FROM station_events
                GROUP BY train_no
            ) latest ON se.train_no = latest.train_no AND se.seq = latest.max_seq AND se.run_date = latest.max_date
            """
        )
        events_rows = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT from_code, to_code, speed_limit_kmph, cause
            FROM speed_restrictions
            WHERE is_active = 1
            """
        )
        tsr_rows = [dict(r) for r in cur.fetchall()]

    return {
        "trains": train_rows,
        "routes": all_routes,
        "events": events_rows,
        "tsrs": tsr_rows,
    }


def get_active_route_station_codes(db: Database) -> List[str]:
    """Queries distinct station codes that have active routes."""
    with db.transaction() as cur:
        cur.execute("SELECT DISTINCT station_code FROM route_stations")
        return [r["station_code"] for r in cur.fetchall()]
