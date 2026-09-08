"""Data access and service layer for stations, platform gantt, and connections."""

from __future__ import annotations

from typing import Any, Dict, Optional
from data.db import Database


def get_station_summary_raw(db: Database, station_code: str) -> Optional[Dict[str, Any]]:
    """Queries station metadata and live counts for the station summary endpoint."""
    with db.transaction() as cur:
        cur.execute("SELECT code, name, zone, platforms FROM stations WHERE code = ?", (station_code,))
        station = cur.fetchone()
        if not station:
            return None

        cur.execute("SELECT COUNT(DISTINCT train_no) AS count FROM route_stations WHERE station_code = ?", (station_code,))
        active_trains = int(cur.fetchone()["count"])

        cur.execute(
            "SELECT AVG(COALESCE(delay_arr_min, delay_dep_min, 0)) AS avg_delay FROM station_events WHERE station_code = ?",
            (station_code,),
        )
        avg_delay_row = cur.fetchone()

        cur.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE target_role IN ('station_master', 'dy_sm') AND state IN ('queued', 'sent', 'escalated')",
        )
        advisories_row = cur.fetchone()

        cur.execute(
            "SELECT COUNT(*) AS count FROM crew_rosters WHERE station_code = ? AND status = 'BREACH_WARNING'",
            (station_code,),
        )
        crew_row = cur.fetchone()

    return {
        "station": dict(station),
        "active_trains": active_trains,
        "avg_delay": float(avg_delay_row["avg_delay"]) if avg_delay_row and avg_delay_row["avg_delay"] is not None else 0.0,
        "pending_advisories": int(advisories_row["count"]) if advisories_row else 0,
        "crew_warnings": int(crew_row["count"]) if crew_row else 0,
    }


def get_station_gantt_metadata(db: Database, station_code: str) -> Optional[Dict[str, Any]]:
    """Queries station name and platform capacity for platform gantt."""
    with db.transaction() as cur:
        cur.execute("SELECT name, platforms FROM stations WHERE code = ?", (station_code,))
        row = cur.fetchone()
        return dict(row) if row else None
