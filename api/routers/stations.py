"""Station details, platform Gantt, re-optimization, and connections router."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import assert_station_scope, require_role
from api.schemas import (
    PlatformGanttBlock,
    PlatformGanttConflict,
    ReoptimizeRequest,
    ReoptimizeResponse,
    StationGanttResponse,
    StationSummaryResponse,
)
from api.services.station_service import (
    get_station_gantt_metadata,
    get_station_summary_raw,
)
from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock
from engine.ops import ConnectionCustodyEngine, PlatformManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stations/{code}", response_model=StationSummaryResponse)
def get_station_summary(code: str):
    """Returns the station contract consumed by the authenticated dashboard shell."""
    station_code = code.strip().upper()
    db = get_db()
    clock = get_clock()

    raw = get_station_summary_raw(db, station_code)
    if not raw:
        raise HTTPException(
            status_code=404,
            detail={"code": "STATION_NOT_FOUND", "message": f"Station {station_code} not found", "retryable": False},
        )

    station = raw["station"]
    conflicts = 0
    try:
        _, conflicts_list = PlatformManager(db).get_station_gantt(station_code)
        conflicts = len(conflicts_list)
    except Exception:
        conflicts = 0

    zone = station["zone"] or "Railway"
    name = station["name"]
    return StationSummaryResponse(
        code=station["code"],
        name=name,
        fullName=f"{name} Junction",
        division=f"{zone} Division",
        zone=zone,
        platformsCount=int(station["platforms"] or 0),
        activeTrainsCount=raw["active_trains"],
        platformConflictsCount=conflicts,
        pendingAdvisoriesCount=raw["pending_advisories"],
        crewWarningsCount=raw["crew_warnings"],
        corridorAvgDelayMinutes=round(raw["avg_delay"], 1),
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.get("/stations/{code}/gantt", response_model=StationGanttResponse)
def get_station_gantt(code: str):
    """Returns platform occupancy Gantt blocks and detected conflicts for a station."""
    station_code = code.upper()
    db = get_db()
    clock = get_clock()
    pm = PlatformManager(db)

    stn_row = get_station_gantt_metadata(db, station_code)
    if not stn_row:
        raise HTTPException(
            status_code=404,
            detail={"code": "STATION_NOT_FOUND", "message": f"Station {station_code} not found", "retryable": False},
        )

    blocks, conflicts = pm.get_station_gantt(station_code)

    return StationGanttResponse(
        station_code=station_code,
        station_name=stn_row["name"],
        total_platforms=int(stn_row["platforms"]),
        conflicts_count=len(conflicts),
        blocks=[PlatformGanttBlock(**b.to_dict()) for b in blocks],
        conflicts=[PlatformGanttConflict(**c.to_dict()) for c in conflicts],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.post("/stations/{code}/reoptimize", response_model=ReoptimizeResponse)
def reoptimize_station_platforms(
    code: str,
    body: Optional[ReoptimizeRequest] = None,
    current_user: dict = Depends(require_role(["station_master", "dy_sm", "admin"])),
):
    """One-click self-healing platform re-optimizer resolving all conflicts in <2s."""
    station_code = code.upper()
    assert_station_scope(current_user, station_code)
    db = get_db()
    clock = get_clock()
    pm = PlatformManager(db)
    target_date = body.target_date if body else None
    blocks, _ = pm.get_station_gantt(station_code, target_date=target_date)
    reopt_blocks, diff = pm.reoptimize_platforms(station_code, blocks)

    return ReoptimizeResponse(
        station_code=station_code,
        conflicts_before=diff.conflicts_before,
        conflicts_after=diff.conflicts_after,
        resolved_conflicts=diff.resolved_conflicts,
        swaps_performed=diff.swaps_performed,
        execution_time_seconds=diff.execution_time_seconds,
        blocks=[PlatformGanttBlock(**b.to_dict()) for b in reopt_blocks],
        updated_at=clock.now_iso(),
        clock_mode=clock.mode,
    )


@router.get("/stations/{code}/connections", response_model=None)
def get_station_connections(
    code: str,
    run_date: Optional[str] = Query(None, description="Date YYYY-MM-DD"),
    min_transfer_min: Optional[int] = Query(
        None, ge=5, le=60, description="Minimum connection transfer time in minutes (defaults to configured value)"
    ),
):
    """Evaluates junction interchange connection feasibility and hold-decision tradeoffs."""
    if min_transfer_min is None:
        min_transfer_min = settings.DEFAULT_MIN_CONNECTION_TIME_MIN
    db = get_db()
    clock = get_clock()
    engine = ConnectionCustodyEngine(db)
    connections = engine.evaluate_station_connections(
        station_code=code,
        run_date=run_date,
        min_connection_time_min=min_transfer_min,
    )

    at_risk_count = sum(1 for c in connections if c.status in ("AT_RISK", "CRITICAL_MISSED", "MISSED"))
    advisories_count = sum(1 for c in connections if c.hold_advisory is not None)

    return {
        "status": "OK",
        "station_code": code.upper(),
        "run_date": run_date or clock.today_str(),
        "total_connections_monitored": len(connections),
        "at_risk_count": at_risk_count,
        "hold_advisories_active": advisories_count,
        "connections": [c.to_dict() for c in connections],
        "as_of": clock.now_iso(),
    }
