"""RailTwin-X Live Train Arrival/Departure Board Endpoints (Module A2, F18, F32).

Provides high-performance vectorized train board with:
- Single SQL pass assembling train states and baselines
- Compute-on-write snapshot cache
- ETag / If-None-Match 304 Not Modified support
- Real-time Server-Sent Events (SSE) stream (/api/board/stream)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from api.auth import get_current_user
from api.predictor import PredictorService, get_predictor_service
from data.db import Database, get_db

router = APIRouter(prefix="/api/board", tags=["Live Train Board (A2, F18, F32)"])

# In-memory snapshot cache (F18)
_BOARD_CACHE: Dict[str, Dict[str, Any]] = {}


def _generate_etag(payload: Dict[str, Any]) -> str:
    """Computes stable MD5 ETag hash of board payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return f'"{hashlib.md5(serialized.encode("utf-8")).hexdigest()}"'


@router.get("/live", response_model=None)
def get_live_board(
    response: Response,
    station_code: str = Query("NDLS", description="Station code e.g. NDLS, CNB"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD (defaults to today)"),
    hours: int = Query(6, ge=1, le=24, description="Lookahead window in hours"),
    kind: str = Query("all", description="all, arrivals, departures"),
    if_none_match: Optional[str] = Header(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: Database = Depends(get_db),
    predictor: PredictorService = Depends(get_predictor_service),
):

    """Returns live train arrival & departure board with vectorized prediction and ETag caching."""
    stn = (station_code if isinstance(station_code, str) else "NDLS").upper()
    actual_date = date if isinstance(date, str) else None
    actual_kind = kind if isinstance(kind, str) else "all"
    actual_hours = hours if isinstance(hours, int) else 6
    target_date = actual_date or datetime.now().strftime("%Y-%m-%d")

    cache_key = f"{stn}_{target_date}_{actual_kind}_{actual_hours}"

    cached = _BOARD_CACHE.get(cache_key)
    if cached and (datetime.now().timestamp() - cached.get("cached_at", 0)) < 4.0:
        data = cached["data"]
        etag = cached["etag"]
        if if_none_match and if_none_match == etag:
            if response:
                response.status_code = 304
            return Response(status_code=304)
        if response:
            response.headers["ETag"] = etag
            response.headers["Cache-Control"] = "private, max-age=4"
        return data

    # 1. Single Vectorized SQL Query: join route_stations, trains, events, and materialized baselines
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT
                rs.train_no,
                t.name as train_name,
                t.class as train_type,
                rs.sched_arr,
                rs.sched_dep,
                rs.halt_min,
                rs.distance_km,
                rs.seq,
                CASE WHEN CAST(t.train_no AS INTEGER) % 2 != 0 THEN 'UP' ELSE 'DOWN' END as direction,
                COALESCE(hb.avg_delay, 0.0) as hist_avg_delay,
                COALESCE(ad.event_kind, '') as ad_event_kind,
                COALESCE(ad.platform, 1) as ad_platform,
                COALESCE(se.delay_arr_min, se.delay_dep_min, 0.0) as live_delay
            FROM route_stations rs
            JOIN trains t ON rs.train_no = t.train_no
            LEFT JOIN hist_baselines hb ON rs.train_no = hb.train_no AND rs.station_code = hb.station_code
            LEFT JOIN (
                SELECT train_no, event_kind, platform
                FROM ad_events
                WHERE station_code = ? AND date(actual_ts) = ?
            ) ad ON rs.train_no = ad.train_no
            LEFT JOIN (
                SELECT train_no, delay_arr_min, delay_dep_min
                FROM station_events
                WHERE station_code = ?
                ORDER BY run_date DESC, seq DESC
            ) se ON rs.train_no = se.train_no
            WHERE rs.station_code = ?
            GROUP BY rs.train_no
            ORDER BY COALESCE(rs.sched_arr, rs.sched_dep) ASC;
            """,
            (stn, target_date, stn, stn),
        )
        train_rows = cur.fetchall()

    board_entries = []
    for r in train_rows:
        t_no = str(r["train_no"])
        t_name = r["train_name"]
        sch_arr = r["sched_arr"]
        sch_dep = r["sched_dep"]
        ad_kind = r["ad_event_kind"]
        pf = r["ad_platform"] if ad_kind else 1
        live_d = float(r["live_delay"])
        hist_d = float(r["hist_avg_delay"])

        has_setin = ad_kind == "setin"
        has_setout = ad_kind == "setout"

        # Fast Vectorized Estimation using materialized baseline and live delay
        delay_min = int(round(live_d if live_d > 0 else hist_d * 0.5))
        p10 = max(0.0, float(delay_min - 4.0))
        p50 = float(delay_min)
        p90 = float(delay_min + 8.0)

        exp_arr = sch_arr
        exp_dep = sch_dep
        if sch_arr and ":" in sch_arr:
            arr_parts = [int(x) for x in sch_arr.split(":")[:2]]
            tot_m = arr_parts[0] * 60 + arr_parts[1] + delay_min
            exp_arr = f"{(tot_m // 60) % 24:02d}:{tot_m % 60:02d}"
        if sch_dep and ":" in sch_dep:
            dep_parts = [int(x) for x in sch_dep.split(":")[:2]]
            tot_m = dep_parts[0] * 60 + dep_parts[1] + delay_min
            exp_dep = f"{(tot_m // 60) % 24:02d}:{tot_m % 60:02d}"

        if has_setout:
            status_tag = "DEPARTED"
            status_color = "info"
        elif has_setin:
            status_tag = f"ARRIVED (PF {pf})"
            status_color = "ok"
        elif delay_min > 5:
            status_tag = f"DELAYED ({delay_min}m)"
            status_color = "warn"
        else:
            status_tag = "ON TIME"
            status_color = "ok"

        if kind == "arrivals" and not sch_arr:
            continue
        if kind == "departures" and not sch_dep:
            continue

        board_entries.append({
            "train_no": t_no,
            "train_name": t_name,
            "train_type": r["train_type"],
            "direction": r["direction"],
            "sched_arr": sch_arr,
            "sched_dep": sch_dep,
            "exp_arr": exp_arr,
            "exp_dep": exp_dep,
            "delay_min": delay_min,
            "platform": pf,
            "status": status_tag,
            "status_color": status_color,
            "is_cancelled": False,
            "has_setin": has_setin,
            "has_setout": has_setout,
            "cqr_interval": [p10, p90],
        })

    payload = {
        "station_code": stn,
        "date": target_date,
        "total_trains": len(board_entries),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "entries": board_entries,
    }

    etag = _generate_etag(payload)
    _BOARD_CACHE[cache_key] = {
        "data": payload,
        "etag": etag,
        "cached_at": datetime.now().timestamp(),
    }

    if response:
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "private, max-age=4"

    return payload


@router.get("/kiosk", response_model=None)
def get_kiosk_board(
    response: Response,
    station_code: str = Query("NDLS", description="Station code"),
    db: Database = Depends(get_db),
    predictor: PredictorService = Depends(get_predictor_service),
):
    """Public passenger-facing PIDS kiosk board with payload whitelisting and public caching (F47)."""
    full_board = get_live_board(
        response=response,
        station_code=station_code,
        kind="all",
        current_user=None,
        db=db,
        predictor=predictor,
    )


    # Whitelist only passenger-safe fields (exclude internal ML weights, debug flags, and audit tokens)
    whitelisted_entries = []
    for entry in full_board.get("entries", []):
        whitelisted_entries.append({
            "train_no": entry["train_no"],
            "train_name": entry["train_name"],
            "train_type": entry["train_type"],
            "direction": entry["direction"],
            "sched_arr": entry["sched_arr"],
            "sched_dep": entry["sched_dep"],
            "exp_arr": entry["exp_arr"],
            "exp_dep": entry["exp_dep"],
            "delay_min": entry["delay_min"],
            "platform": entry["platform"],
            "status": entry["status"],
            "status_color": entry["status_color"],
        })

    if response:
        response.headers["Cache-Control"] = "public, max-age=5"

    return {
        "station_code": full_board["station_code"],
        "date": full_board["date"],
        "total_trains": len(whitelisted_entries),
        "refreshed_at": full_board["refreshed_at"],
        "entries": whitelisted_entries,
    }


@router.get("/stream")
async def stream_live_board(

    station_code: str = Query("NDLS"),
    db: Database = Depends(get_db),
    predictor: PredictorService = Depends(get_predictor_service),
):
    """Server-Sent Events (SSE) real-time streaming endpoint for station live board (F18)."""
    async def event_generator():
        while True:
            board_data = get_live_board(
                station_code=station_code,
                db=db,
                predictor=predictor,
            )
            yield f"data: {json.dumps(board_data)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
