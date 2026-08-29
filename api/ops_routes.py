"""RailTwin-X Operational Ground Truth & Movement Endpoints (Modules A4 & A6).

Implements one-tap Set-In / Set-Out actuals confirmation (Bucket C training data capture point)
and shunting / non-timetable movement logging with conflict checking.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import get_current_user, require_role
from data.audit import record_audit
from data.db import Database, get_db
from notifications.dispatcher import notify


router = APIRouter(prefix="/api/ops", tags=["Station Operations & Actuals (A4 & A6)"])


class SetInRequest(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    platform: int = Field(..., ge=1, le=24, description="Actual platform occupied")
    actual_ts: Optional[str] = Field(None, description="ISO timestamp or HH:MM (defaults to now)")
    predicted_ts: Optional[str] = None


class SetOutRequest(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    platform: int = Field(..., ge=1, le=24, description="Platform departed from")
    actual_ts: Optional[str] = Field(None, description="ISO timestamp or HH:MM (defaults to now)")


class ShuntingMoveCreate(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    move_type: str = Field("loco_attach", description="loco_attach, loco_detach, rake_release, yard_shunt, empty_haul")
    loco_id: str = Field(..., description="Locomotive identifier e.g. WAP7-30214")
    rake_id: Optional[str] = Field(None, description="Rake identifier")
    from_track: str = Field(..., description="Starting track or platform e.g. PF1, Yard-Line-4")
    to_track: str = Field(..., description="Destination track or platform e.g. Siding-2, PF3")
    start_time: str = Field(..., description="Scheduled start HH:MM")
    end_time: str = Field(..., description="Scheduled completion HH:MM")
    notes: Optional[str] = None


class ShuntingStatusUpdate(BaseModel):
    status: str = Field(..., description="REQUESTED, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED")
    notes: Optional[str] = None


@router.post("/setin/{train_no}", response_model=Dict[str, Any])
def record_set_in(
    train_no: str,
    req: SetInRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Records human-confirmed ACTUAL train arrival (Set-In) at a platform."""
    now_iso = datetime.now(timezone.utc).isoformat()
    actual_time = req.actual_ts or now_iso
    stn = req.station_code.upper()
    run_date = datetime.now().strftime("%Y-%m-%d")
    run_id = f"RUN-{train_no}-{run_date}"

    # Calculate discrepancy if predicted_ts or ETA p50 exists
    discrepancy_min = 0.0
    discrepancy_flag = 0
    if req.predicted_ts:
        try:
            pred_dt = datetime.fromisoformat(req.predicted_ts)
            act_dt = datetime.fromisoformat(actual_time)
            discrepancy_min = abs((act_dt - pred_dt).total_seconds() / 60.0)
            if discrepancy_min > 15.0:
                discrepancy_flag = 1
        except Exception:
            pass

    with db.transaction() as cur:
        # 1. Record to ad_events (The Golden Ground Truth Table)
        cur.execute(
            """
            INSERT INTO ad_events (
                run_id, train_no, station_code, event_kind, actual_ts,
                platform, predicted_ts, discrepancy_min, discrepancy_flag,
                source, confirmed_by, created_at
            ) VALUES (?, ?, ?, 'setin', ?, ?, ?, ?, ?, 'human', ?, ?);
            """,
            (
                run_id,
                train_no,
                stn,
                actual_time,
                req.platform,
                req.predicted_ts,
                discrepancy_min,
                discrepancy_flag,
                current_user["id"],
                now_iso,
            ),
        )
        event_id = cur.lastrowid

        # 2. Update platform state to OCCUPIED
        cur.execute(
            """
            INSERT INTO platform_states (station_code, platform, state, occupied_by_train, since, reason, updated_by)
            VALUES (?, ?, 'OCCUPIED', ?, ?, 'Train Set-In', ?)
            ON CONFLICT(station_code, platform) DO UPDATE SET
                state = 'OCCUPIED',
                occupied_by_train = excluded.occupied_by_train,
                since = excluded.since,
                reason = excluded.reason,
                updated_by = excluded.updated_by;
            """,
            (stn, req.platform, train_no, now_iso, current_user["id"]),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TRAIN_SET_IN_CONFIRMED",
            table_name="ad_events",
            record_id=event_id,
            after_state={"train_no": train_no, "station_code": stn, "platform": req.platform, "actual_ts": actual_time},
        )

    # Emit notification
    notify(
        event_type="TRAIN_ARRIVED",
        target_roles=["station_master", "dy_sm", "crew_controller", "viewer"],
        severity="info",
        title=f"Train #{train_no} Arrived on Platform {req.platform}",
        message=f"Train #{train_no} set-in confirmed at {stn} PF{req.platform} by {current_user['full_name']}.",
        payload={"train_no": train_no, "station_code": stn, "platform": req.platform},
        station_code=stn,
        db=db,
    )

    return {
        "event_id": event_id,
        "train_no": train_no,
        "station_code": stn,
        "platform": req.platform,
        "status": "ARRIVED",
        "actual_ts": actual_time,
        "discrepancy_min": discrepancy_min,
        "discrepancy_flag": bool(discrepancy_flag),
    }


@router.post("/setout/{train_no}", response_model=Dict[str, Any])
def record_set_out(
    train_no: str,
    req: SetOutRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Records human-confirmed ACTUAL train departure (Set-Out) and frees the platform."""
    now_iso = datetime.now(timezone.utc).isoformat()
    actual_time = req.actual_ts or now_iso
    stn = req.station_code.upper()
    run_date = datetime.now().strftime("%Y-%m-%d")
    run_id = f"RUN-{train_no}-{run_date}"

    with db.transaction() as cur:
        # 1. Record to ad_events
        cur.execute(
            """
            INSERT INTO ad_events (
                run_id, train_no, station_code, event_kind, actual_ts,
                platform, source, confirmed_by, created_at
            ) VALUES (?, ?, ?, 'setout', ?, ?, 'human', ?, ?);
            """,
            (
                run_id,
                train_no,
                stn,
                actual_time,
                req.platform,
                current_user["id"],
                now_iso,
            ),
        )
        event_id = cur.lastrowid

        # 2. Release platform to FREE
        cur.execute(
            """
            INSERT INTO platform_states (station_code, platform, state, occupied_by_train, since, reason, updated_by)
            VALUES (?, ?, 'FREE', NULL, ?, 'Train Set-Out', ?)
            ON CONFLICT(station_code, platform) DO UPDATE SET
                state = 'FREE',
                occupied_by_train = NULL,
                since = excluded.since,
                reason = excluded.reason,
                updated_by = excluded.updated_by;
            """,
            (stn, req.platform, now_iso, current_user["id"]),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TRAIN_SET_OUT_CONFIRMED",
            table_name="ad_events",
            record_id=event_id,
            after_state={"train_no": train_no, "station_code": stn, "platform": req.platform, "actual_ts": actual_time},
        )

    # Emit notification
    notify(
        event_type="TRAIN_DEPARTED",
        target_roles=["station_master", "dy_sm", "section_controller", "viewer"],
        severity="info",
        title=f"Train #{train_no} Departed Platform {req.platform}",
        message=f"Train #{train_no} set-out confirmed from {stn} PF{req.platform}. Platform is now FREE.",
        payload={"train_no": train_no, "station_code": stn, "platform": req.platform},
        station_code=stn,
        db=db,
    )

    return {
        "event_id": event_id,
        "train_no": train_no,
        "station_code": stn,
        "platform": req.platform,
        "status": "DEPARTED",
        "actual_ts": actual_time,
    }


@router.get("/ad-events", response_model=List[Dict[str, Any]])
def list_ad_events(
    station_code: Optional[str] = Query(None),
    train_no: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Fetches confirmed arrival and departure ground-truth logs."""
    query = "SELECT * FROM ad_events WHERE 1=1"
    params: List[Any] = []

    if station_code:
        query += " AND station_code = ?"
        params.append(station_code.upper())
    if train_no:
        query += " AND train_no = ?"
        params.append(train_no)

    query += " ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    with db.transaction() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "run_id": r["run_id"],
            "train_no": r["train_no"],
            "station_code": r["station_code"],
            "event_kind": r["event_kind"],
            "actual_ts": r["actual_ts"],
            "platform": r["platform"],
            "predicted_ts": r["predicted_ts"],
            "discrepancy_min": r["discrepancy_min"],
            "discrepancy_flag": bool(r["discrepancy_flag"]),
            "source": r["source"],
            "confirmed_by": r["confirmed_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/shunting", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_shunting_move(
    req: ShuntingMoveCreate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "engineer", "admin"])),
    db: Database = Depends(get_db),
):
    """Logs a non-timetable shunting move and checks for platform conflicts."""
    now_iso = datetime.now(timezone.utc).isoformat()
    stn = req.station_code.upper()

    # Check if target track/platform has overlapping trains in timetable or platform_states
    conflict_warning = None
    with db.transaction() as cur:
        if "PF" in req.to_track.upper():
            try:
                pf_num = int(req.to_track.upper().replace("PF", "").strip())
                cur.execute(
                    "SELECT state, occupied_by_train FROM platform_states WHERE station_code = ? AND platform = ?;",
                    (stn, pf_num),
                )
                pf_row = cur.fetchone()
                if pf_row and pf_row["state"] == "OCCUPIED":
                    conflict_warning = f"Platform {pf_num} is currently OCCUPIED by Train #{pf_row['occupied_by_train']}."
            except Exception:
                pass

        cur.execute(
            """
            INSERT INTO shunting_moves (
                station_code, move_type, loco_id, rake_id, from_track,
                to_track, start_time, end_time, status, notes, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'REQUESTED', ?, ?, ?);
            """,
            (
                stn,
                req.move_type,
                req.loco_id,
                req.rake_id,
                req.from_track,
                req.to_track,
                req.start_time,
                req.end_time,
                req.notes,
                current_user["id"],
                now_iso,
            ),
        )
        move_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="SHUNTING_MOVE_REQUESTED",
            table_name="shunting_moves",
            record_id=move_id,
            after_state={"loco_id": req.loco_id, "from": req.from_track, "to": req.to_track},
        )

    return {
        "id": move_id,
        "status": "REQUESTED",
        "station_code": stn,
        "loco_id": req.loco_id,
        "conflict_warning": conflict_warning,
    }


@router.get("/shunting", response_model=List[Dict[str, Any]])
def list_shunting_moves(
    station_code: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists shunting and non-timetable yard movements."""
    query = "SELECT * FROM shunting_moves WHERE 1=1"
    params: List[Any] = []

    if station_code:
        query += " AND station_code = ?"
        params.append(station_code.upper())
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter.upper())

    query += " ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    with db.transaction() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "station_code": r["station_code"],
            "move_type": r["move_type"],
            "loco_id": r["loco_id"],
            "rake_id": r["rake_id"],
            "from_track": r["from_track"],
            "to_track": r["to_track"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "status": r["status"],
            "notes": r["notes"],
            "created_by": r["created_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.put("/shunting/{move_id}/status", response_model=Dict[str, Any])
def update_shunting_status(
    move_id: int,
    req: ShuntingStatusUpdate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "engineer", "admin"])),
    db: Database = Depends(get_db),
):
    """Updates the status of a shunting movement."""
    with db.transaction() as cur:
        cur.execute("SELECT * FROM shunting_moves WHERE id = ?;", (move_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Shunting move not found.")

        cur.execute(
            """
            UPDATE shunting_moves
            SET status = ?, notes = COALESCE(?, notes)
            WHERE id = ?;
            """,
            (req.status.upper(), req.notes, move_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="SHUNTING_STATUS_UPDATED",
            table_name="shunting_moves",
            record_id=move_id,
            after_state={"status": req.status.upper()},
        )

    return {"id": move_id, "status": req.status.upper()}
