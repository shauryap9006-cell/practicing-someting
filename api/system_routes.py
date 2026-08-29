"""RailTwin-X System Diagnostics & Degraded Mode Engine (Module I6).

Provides system health checks, telemetry feed freshness monitoring,
external gateway statuses, and degraded mode indicators for the Station OS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from config import settings
from data.db import Database, get_db

router = APIRouter(prefix="/api/system", tags=["System Diagnostics & Degraded Mode (I6)"])


@router.get("/status", response_model=Dict[str, Any])
def get_system_status(db: Database = Depends(get_db)):
    """Returns comprehensive Station OS health metrics, telemetry freshness, and degraded mode state."""
    now_utc = datetime.now(timezone.utc)
    degraded_reasons: List[str] = []

    # 1. Check Database Health
    db_ok = True
    table_counts = {}
    try:
        table_counts = db.table_counts()
    except Exception as e:
        db_ok = False
        degraded_reasons.append(f"Database operational error: {str(e)}")

    # 2. Check Telemetry Freshness from run_snapshots
    last_snapshot_ts = None
    telemetry_age_sec = 0
    with db.transaction() as cur:
        try:
            cur.execute("SELECT MAX(ts) as max_ts FROM run_snapshots;")
            row = cur.fetchone()
            if row and row["max_ts"]:
                last_snapshot_ts = row["max_ts"]
                try:
                    snap_dt = datetime.fromisoformat(last_snapshot_ts.replace("Z", "+00:00"))
                    telemetry_age_sec = int((now_utc - snap_dt).total_seconds())
                except Exception:
                    telemetry_age_sec = 0
        except Exception:
            pass

    if telemetry_age_sec > 900:  # > 15 minutes
        degraded_reasons.append(f"Telemetry feed is STALE ({telemetry_age_sec // 60} minutes old). Operating on last known truth.")

    # 3. Check ML Artifacts Presence
    ml_ok = True
    required_artifacts = [
        settings.ARTIFACTS_DIR / "manifest.json",
        settings.ARTIFACTS_DIR / "model_direct_q50.txt",
        settings.ARTIFACTS_DIR / "model_gru_challenger.pt",
    ]
    for art in required_artifacts:
        if not art.exists():
            ml_ok = False
            degraded_reasons.append(f"Missing ML artifact: {art.name}")

    is_degraded = len(degraded_reasons) > 0

    return {
        "status": "DEGRADED" if is_degraded else "HEALTHY",
        "is_degraded": is_degraded,
        "degraded_reasons": degraded_reasons,
        "database_connected": db_ok,
        "ml_models_loaded": ml_ok,
        "last_telemetry_snapshot": last_snapshot_ts,
        "telemetry_age_seconds": telemetry_age_sec,
        "is_telemetry_stale": telemetry_age_sec > 900,
        "local_timestamp": now_utc.isoformat(),
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

