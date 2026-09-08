from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from config import settings
from data.db import Database, get_db
from engine.clocks import IST_TIMEZONE, ist_now

router = APIRouter(prefix="/api/system", tags=["System Diagnostics & Degraded Mode (I6)"])
logger = logging.getLogger(__name__)

REQUIRED_ML_ARTIFACTS = ("manifest.json", "model_direct_q50.txt", "model_gru_challenger.pt")


@router.get("/status", response_model=Dict[str, Any])
def get_system_status(db: Database = Depends(get_db)):
    """Returns comprehensive Station OS health metrics, telemetry freshness, and degraded mode state."""
    now_ist = ist_now()
    degraded_reasons: List[str] = []
    stale_after = int(settings.TELEMETRY_STALE_SECONDS)

    # 1. Check Database Health (never echo driver errors to unauthenticated callers)
    db_ok = True
    table_counts: Dict[str, int] = {}
    try:
        table_counts = db.table_counts()
    except Exception:
        logger.exception("system status: database check failed")
        db_ok = False
        degraded_reasons.append("Database unavailable.")

    # 2. Check Telemetry Freshness from run_snapshots
    last_snapshot_ts = None
    telemetry_age_sec = 0
    if db_ok:
        try:
            with db.transaction() as cur:
                cur.execute("SELECT MAX(ts) as max_ts FROM run_snapshots;")
                row = cur.fetchone()
            if row and row["max_ts"]:
                last_snapshot_ts = row["max_ts"]
                try:
                    snap_dt = datetime.fromisoformat(str(last_snapshot_ts).replace("Z", "+00:00"))
                    if snap_dt.tzinfo is None:
                        snap_dt = snap_dt.replace(tzinfo=IST_TIMEZONE)
                    telemetry_age_sec = max(0, int((now_ist - snap_dt).total_seconds()))
                except ValueError:
                    telemetry_age_sec = 0
        except Exception:
            logger.exception("system status: telemetry freshness check failed")

    is_stale = telemetry_age_sec > stale_after
    if is_stale:
        degraded_reasons.append(
            f"Telemetry feed is STALE ({telemetry_age_sec // 60} minutes old). Operating on last known truth."
        )

    # 3. Check ML Artifacts Presence
    ml_ok = True
    for name in REQUIRED_ML_ARTIFACTS:
        if not (settings.ARTIFACTS_DIR / name).is_file():
            ml_ok = False
            degraded_reasons.append(f"Missing ML artifact: {name}")

    is_degraded = len(degraded_reasons) > 0

    return {
        "status": "DEGRADED" if is_degraded else "HEALTHY",
        "is_degraded": is_degraded,
        "degraded_reasons": degraded_reasons,
        "database_connected": db_ok,
        "ml_models_loaded": ml_ok,
        "last_telemetry_snapshot": last_snapshot_ts,
        "telemetry_age_seconds": telemetry_age_sec,
        "telemetry_stale_after_seconds": stale_after,
        "is_telemetry_stale": is_stale,
        "local_timestamp": now_ist.isoformat(),
        "tables_summary": {
            "stations": table_counts.get("stations", 0),
            "trains": table_counts.get("trains", 0),
            "station_events": table_counts.get("station_events", 0),
            "ad_events": table_counts.get("ad_events", 0),
            "timetable_entries": table_counts.get("timetable_entries", 0),
        },
    }


@router.get("/model-info", response_model=Dict[str, Any])
def get_system_model_info():
    """Returns governance information, artifact SHA, and serving status for the promoted model (F15)."""
    from api.predictor import get_predictor_service

    predictor = get_predictor_service()
    return predictor.get_model_info()
