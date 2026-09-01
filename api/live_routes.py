"""RailTwin-X Live Position Tracking & Delay Attribution Routes (Pipeline 07, Phase A6).

Exposes high-performance REST and SSE endpoints for:
- Live train kinematics, dead-reckoning, and operational context: GET /v1/trains/{train_no}/live
- Causal why-late delay attribution: GET /v1/trains/{train_no}/why-late
- All active corridor train positions: GET /v1/live/positions
- Real-time Server-Sent Events stream: GET /v1/live/stream
- Frontend runtime configuration: GET /v1/meta/config
"""

from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from config import settings
from data.db import Database, get_db
from engine.clocks import get_clock, IST_TIMEZONE
from engine.context import ContextEngine, get_context_engine
from engine.attribution import LiveAttributionEngine, get_attribution_engine
from engine.live_tracker import LivePositionTracker, get_live_tracker

router = APIRouter(tags=["Live Tracking & Attribution (Pipeline 07)"])

# In-memory response cache for live positions
_POSITION_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_tracker_dep() -> LivePositionTracker:
    return get_live_tracker()


def _get_context_dep() -> ContextEngine:
    return get_context_engine()


def _get_attribution_dep() -> LiveAttributionEngine:
    return get_attribution_engine()


@router.get("/v1/meta/config", response_model=None)
@router.get("/api/v1/meta/config", response_model=None)
def get_meta_config() -> Dict[str, Any]:
    """Returns frontend-relevant runtime constants, intervals, budgets, and color tokens."""
    return {
        "status": "OK",
        "app_name": settings.APP_NAME,
        "env": settings.ENV,
        "demo_mode": getattr(settings, "DEMO_MODE", False),
        "demo_scenario_date": getattr(settings, "DEMO_SCENARIO_DATE", "2026-01-15"),
        "intervals": {
            "live_tracker_interval_seconds": settings.LIVE_TRACKER_INTERVAL_SECONDS,
            "live_station_poll_seconds": settings.LIVE_STATION_POLL_SECONDS,
            "live_sse_pulse_seconds": settings.LIVE_SSE_PULSE_SECONDS,
            "position_cache_ttl_seconds": settings.POSITION_CACHE_TTL_SECONDS,
            "context_cache_ttl_seconds": settings.CONTEXT_CACHE_TTL_SECONDS,
            "weather_cache_minutes": settings.WEATHER_CACHE_MINUTES,
        },
        "thresholds": {
            "attribution_delta_min": settings.ATTRIBUTION_DELTA_MIN,
            "attribution_unexplained_tolerance_min": settings.ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN,
            "confidence_tau_seconds": settings.CONFIDENCE_TAU_SECONDS,
            "dead_reckon_min_confidence": settings.DEAD_RECKON_MIN_CONFIDENCE,
            "fog_max_temp_celsius": settings.FOG_MAX_TEMP_CELSIUS,
            "fog_min_humidity_percent": settings.FOG_MIN_HUMIDITY_PERCENT,
            "heavy_rain_threshold_mm": settings.HEAVY_RAIN_THRESHOLD_MM,
            "crew_duty_hours_cap": settings.CREW_DUTY_HOURS_CAP,
        },
        "budgets": {
            "live_poll_tpm_budget": settings.LIVE_POLL_TPM_BUDGET,
        },
        "delay_colors": {
            "on_time_max_min": 15,
            "moderate_max_min": 60,
            "color_on_time": "#10B981",    # emerald-500
            "color_moderate": "#F59E0B",   # amber-500
            "color_severe": "#EF4444",     # red-500
        },
        "attribution_colors": {
            "RAKE_INHERIT": "#A855F7",    # Purple
            "TSR_ACTIVE": "#EF4444",      # Red
            "WEATHER_FOG": "#94A3B8",     # Foggy Gray
            "WEATHER_RAIN": "#38BDF8",    # Rain Blue
            "PLATFORM_WAIT": "#F59E0B",   # Amber
            "CONGESTION": "#F97316",      # Orange
            "UNEXPLAINED": "#64748B",     # Slate Gray
        },
    }


@router.get("/v1/trains/{train_no}/live", response_model=None)
@router.get("/api/v1/trains/{train_no}/live", response_model=None)
def get_train_live(
    train_no: str,
    run_date: Optional[str] = Query(None, description="Run date YYYY-MM-DD (defaults to clock today)"),
    db: Database = Depends(get_db),
    tracker: LivePositionTracker = Depends(_get_tracker_dep),
    context_engine: ContextEngine = Depends(_get_context_dep),
    attribution_engine: LiveAttributionEngine = Depends(_get_attribution_dep),
) -> Dict[str, Any]:
    """Returns live kinematic position, enriched operational context, and why-late attribution summary."""
    clean_no = train_no.strip()

    # 1. Validate train existence
    with db.transaction() as cur:
        cur.execute("SELECT train_no, name, class FROM trains WHERE train_no = ?", (clean_no,))
        train_row = cur.fetchone()
        if not train_row:
            raise HTTPException(status_code=404, detail=f"Train '{clean_no}' not found in timetable registry.")

    clock = get_clock()
    target_date = run_date or clock.today_str()
    cache_key = f"{clean_no}:{target_date}"
    now_ts = clock.now().timestamp()

    # Check cache
    cached = _POSITION_CACHE.get(cache_key)
    if cached and (now_ts - cached["timestamp"]) < settings.POSITION_CACHE_TTL_SECONDS:
        return cached["data"]

    # 2. Get Live Position
    pos = tracker.get_live_position(clean_no, target_date)
    if not pos:
        # Construct graceful fallback position
        with db.transaction() as cur:
            cur.execute(
                """
                SELECT rs.station_code, s.lat, s.lon, s.name as station_name
                FROM route_stations rs
                JOIN stations s ON rs.station_code = s.code
                WHERE rs.train_no = ? ORDER BY rs.seq ASC LIMIT 1
                """,
                (clean_no,),
            )
            first_stn = cur.fetchone()

        pos = {
            "train_no": clean_no,
            "run_date": target_date,
            "lat": float(first_stn["lat"]) if first_stn else 28.6143,
            "lng": float(first_stn["lon"]) if first_stn else 77.2188,
            "lon": float(first_stn["lon"]) if first_stn else 77.2188,
            "current_station_code": first_stn["station_code"] if first_stn else "NDLS",
            "next_station_code": None,
            "prev_station_code": None,
            "section_id": None,
            "speed_kmh": 0.0,
            "heading": 90.0,
            "delay_minutes": 0.0,
            "confidence": 1.0,
            "progress_pct": 0.0,
            "is_dead_reckoned": False,
            "basis": "schedule_only",
            "source": "fallback",
            "status": "NOT_STARTED",
            "last_event_time": clock.now().isoformat(),
            "updated_at": clock.now().isoformat(),
        }

    # 3. Enrich with Context Engine
    ctx = context_engine.enrich(
        train_no=clean_no,
        run_date=target_date,
        current_station=pos.get("current_station_code"),
        current_km=float(pos.get("progress_pct", 0.0)) * 7.85,
        as_of_time=clock.now(),
    )

    # 4. Get Why-Late Attribution Summary
    why_late = attribution_engine.get_why_late_summary(clean_no, target_date)

    response_payload = {
        "train_no": clean_no,
        "train_name": train_row["name"],
        "train_class": train_row["class"],
        "run_date": target_date,
        "position": pos,
        "context": ctx.to_dict(),
        "why_late": why_late,
        "as_of": clock.now().isoformat(),
    }

    _POSITION_CACHE[cache_key] = {
        "timestamp": now_ts,
        "data": response_payload,
    }

    return response_payload


@router.get("/v1/trains/{train_no}/why-late", response_model=None)
@router.get("/api/v1/trains/{train_no}/why-late", response_model=None)
def get_train_why_late(
    train_no: str,
    run_date: Optional[str] = Query(None, description="Run date YYYY-MM-DD (defaults to clock today)"),
    db: Database = Depends(get_db),
    attribution_engine: LiveAttributionEngine = Depends(_get_attribution_dep),
) -> Dict[str, Any]:
    """Returns causal delay autopsy breakdown, ranked causes, and mathematical accounting proof."""
    clean_no = train_no.strip()

    with db.transaction() as cur:
        cur.execute("SELECT train_no, name, class FROM trains WHERE train_no = ?", (clean_no,))
        train_row = cur.fetchone()
        if not train_row:
            raise HTTPException(status_code=404, detail=f"Train '{clean_no}' not found in timetable registry.")

    clock = get_clock()
    target_date = run_date or clock.today_str()

    summary = attribution_engine.get_why_late_summary(clean_no, target_date)
    summary["train_name"] = train_row["name"]
    summary["train_class"] = train_row["class"]
    return summary


@router.get("/v1/live/positions", response_model=None)
@router.get("/api/v1/live/positions", response_model=None)
def get_live_positions(
    run_date: Optional[str] = Query(None, description="Run date YYYY-MM-DD (defaults to clock today)"),
    tracker: LivePositionTracker = Depends(_get_tracker_dep),
) -> Dict[str, Any]:
    """Returns real-time kinematic positions for all active corridor trains."""
    clock = get_clock()
    target_date = run_date or clock.today_str()
    positions = tracker.get_all_live_positions(target_date)

    return {
        "status": "OK",
        "count": len(positions),
        "as_of": clock.now().isoformat(),
        "positions": positions,
    }


@router.get("/v1/live/stream", response_model=None)
@router.get("/api/v1/live/stream", response_model=None)
async def stream_live_positions(
    request: Request,
    max_frames: Optional[int] = Query(None, description="Optional limit on number of SSE frames"),
    tracker: LivePositionTracker = Depends(_get_tracker_dep),
):
    """Server-Sent Events (SSE) stream broadcasting real-time train positions and delay chips."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    tracker.subscribe(queue)

    async def event_generator():
        frames_sent = 0
        try:
            # Initial burst: emit current snapshot immediately
            initial_positions = tracker.get_all_live_positions()
            initial_payload = {
                "event": "initial_state",
                "count": len(initial_positions),
                "as_of": get_clock().now().isoformat(),
                "positions": initial_positions,
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"
            frames_sent += 1
            if max_frames and frames_sent >= max_frames:
                return

            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break

                try:
                    # Wait for tracker update broadcast or pulse timeout
                    payload = await asyncio.wait_for(
                        queue.get(),
                        timeout=float(settings.LIVE_SSE_PULSE_SECONDS),
                    )
                    yield f"data: {json.dumps(payload)}\n\n"
                    frames_sent += 1
                    if max_frames and frames_sent >= max_frames:
                        break
                except asyncio.TimeoutError:
                    # Periodic heartbeat pulse
                    positions = tracker.get_all_live_positions()
                    pulse_payload = {
                        "event": "pulse",
                        "count": len(positions),
                        "as_of": get_clock().now().isoformat(),
                        "positions": positions,
                    }
                    yield f"data: {json.dumps(pulse_payload)}\n\n"
                except Exception:
                    break

        finally:
            tracker.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
