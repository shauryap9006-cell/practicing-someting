"""RailTwin-X Live Operational Events Endpoint (Module A2 / Live Wall Monitor).

Provides a public, read-only stream of recent railway operational events:
- Station arrivals and departures from station_events
- Dynamic delay shifts and attribution changes from live_delay_ledger
- Active speed restrictions (TSRs)
- Injected simulation shocks
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from data.db import Database, get_db
from engine.clocks import get_clock

router = APIRouter(tags=["Live Operational Events"])


@router.get("/v1/live/events/recent", response_model=None)
@router.get("/api/v1/live/events/recent", response_model=None)
def get_recent_live_events(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events to return"),
    db: Database = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Returns the most recent operational events, newest first, across all subsystems.

    Data sources:
    1. station_events (recent arrivals & departures)
    2. live_delay_ledger (delay shift events with primary cause)
    3. Active demo shocks (_ACTIVE_SHOCKS from api.demo_routes)
    4. Active speed restrictions (TSRs) from speed_restrictions
    """
    events: List[Dict[str, Any]] = []
    clock = get_clock()
    now_iso = clock.now_iso()

    with db.transaction() as cur:
        # 1. Recent station arrivals and departures
        cur.execute(
            """
            SELECT
                se.event_time,
                se.train_no,
                t.name as train_name,
                se.station_code,
                se.actual_arr,
                se.actual_dep,
                se.delay_arr_min,
                se.delay_dep_min
            FROM station_events se
            LEFT JOIN trains t ON se.train_no = t.train_no
            ORDER BY se.rowid DESC
            LIMIT ?;
            """,
            (limit,),
        )
        for row in cur.fetchall():
            is_dep = row["actual_dep"] is not None
            ev_type = "departure" if is_dep else "arrival"
            delay = int(row["delay_dep_min"] if is_dep else (row["delay_arr_min"] or 0))
            ts = row["event_time"] or row["actual_dep"] or row["actual_arr"] or now_iso
            t_no = str(row["train_no"])
            t_name = row["train_name"]
            stn = row["station_code"]
            action = "departed" if is_dep else "arrived at"
            detail = f"{t_no} {t_name or ''} {action} {stn}, +{delay}m".strip()

            events.append(
                {
                    "ts": str(ts),
                    "type": ev_type,
                    "train_no": t_no,
                    "train_name": t_name,
                    "station_code": stn,
                    "delay_min": delay,
                    "detail": detail,
                }
            )

        # 2. Recent delay shift events from live_delay_ledger
        cur.execute(
            """
            SELECT
                l.timestamp,
                l.train_no,
                t.name as train_name,
                l.delay_change_min,
                l.current_delay_min,
                l.primary_cause
            FROM live_delay_ledger l
            LEFT JOIN trains t ON l.train_no = t.train_no
            ORDER BY l.rowid DESC
            LIMIT ?;
            """,
            (limit,),
        )
        for row in cur.fetchall():
            cur_delay = int(round(float(row["current_delay_min"] or 0)))
            delta = int(round(float(row["delay_change_min"] or 0)))
            sign = "+" if delta >= 0 else ""
            cause = row["primary_cause"] or "delay shift"
            t_no = str(row["train_no"])
            t_name = row["train_name"]
            detail = f"{t_no} {t_name or ''} delay shift: {cause} ({sign}{delta}m, now +{cur_delay}m)".strip()

            events.append(
                {
                    "ts": str(row["timestamp"] or now_iso),
                    "type": "delay_shift",
                    "train_no": t_no,
                    "train_name": t_name,
                    "station_code": None,
                    "delay_min": cur_delay,
                    "detail": detail,
                }
            )

        # 3. Active TSRs from speed_restrictions
        try:
            cur.execute(
                """
                SELECT from_code, to_code, speed_limit_kmph, cause, created_at
                FROM speed_restrictions
                WHERE is_active = 1
                ORDER BY id DESC
                LIMIT 20;
                """
            )
            for row in cur.fetchall():
                tsr_detail = f"TSR {row['from_code']}–{row['to_code']} ({int(row['speed_limit_kmph'])} km/h): {row['cause']}"
                events.append(
                    {
                        "ts": str(row["created_at"] or now_iso),
                        "type": "tsr",
                        "train_no": None,
                        "train_name": None,
                        "station_code": row["from_code"],
                        "delay_min": None,
                        "detail": tsr_detail,
                    }
                )
        except Exception:
            pass

    # 4. Active Injected Demo Shocks (prominently shown on wall)
    try:
        from api.demo_routes import _ACTIVE_SHOCKS

        for shock in _ACTIVE_SHOCKS:
            events.append(
                {
                    "ts": str(shock.get("injected_at") or now_iso),
                    "type": "shock",
                    "train_no": None,
                    "train_name": None,
                    "station_code": shock.get("station"),
                    "delay_min": shock.get("severity_min"),
                    "detail": shock.get("description")
                    or f"Injected shock: {shock.get('event_type')} (+{shock.get('severity_min')}m)",
                }
            )
    except Exception:
        pass

    # Sort newest first (ts descending)
    events.sort(key=lambda e: str(e.get("ts") or ""), reverse=True)
    return events[:limit]
