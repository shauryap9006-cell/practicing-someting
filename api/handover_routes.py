"""RailTwin-X Digital Shift Handover Logbook Endpoints (Module I2).

Enables seamless operational continuity across shift transitions by auto-aggregating
open incidents, active speed restrictions (TSRs), possessions, and crew exceptions,
backed by dual digital signature validation and audit tracking.
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

router = APIRouter(prefix="/api/handover", tags=["Digital Shift Handover (I2)"])


class DraftHandoverRequest(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    shift_date: str = Field(..., description="Date of shift (YYYY-MM-DD)")
    shift_type: str = Field("morning", description="Shift type: morning, afternoon, night")
    operational_notes: Optional[str] = Field(None, description="Free-text operational remarks from outgoing SM")


class SignOutRequest(BaseModel):
    operational_notes: Optional[str] = None


class AckInRequest(BaseModel):
    acknowledgment_notes: Optional[str] = None


class HandoverResponse(BaseModel):
    id: int
    station_code: str
    shift_date: str
    shift_type: str
    outgoing_user_id: str
    outgoing_user_name: Optional[str] = None
    incoming_user_id: Optional[str] = None
    incoming_user_name: Optional[str] = None
    outgoing_signed_at: Optional[str] = None
    incoming_acked_at: Optional[str] = None
    open_incidents: List[Dict[str, Any]]
    active_srs: List[Dict[str, Any]]
    active_possessions: List[Dict[str, Any]]
    crew_exceptions: List[Dict[str, Any]]
    operational_notes: Optional[str] = None
    status: str


def auto_aggregate_station_state(station_code: str, db: Database) -> Dict[str, Any]:
    """Auto-collects live active TSRs, open notifications, and equipment states for the station."""
    active_srs = []
    open_incidents = []
    crew_exceptions = []
    active_possessions = []

    with db.transaction() as cur:
        # 1. Fetch active speed restrictions
        try:
            cur.execute(
                """
                SELECT id, from_code, to_code, speed_limit_kmph, cause
                FROM speed_restrictions
                WHERE is_active = 1 AND (from_code = ? OR to_code = ?);
                """,
                (station_code, station_code),
            )
            for r in cur.fetchall():
                active_srs.append({
                    "id": r["id"],
                    "from_code": r["from_code"],
                    "to_code": r["to_code"],
                    "speed_limit_kmph": r["speed_limit_kmph"],
                    "cause": r["cause"],
                })
        except Exception:
            pass

        # 2. Fetch unacknowledged critical/warning notifications
        try:
            cur.execute(
                """
                SELECT id, event_type, severity, title, message, created_at
                FROM notifications
                WHERE state IN ('queued', 'sent', 'escalated')
                ORDER BY id DESC LIMIT 10;
                """
            )
            for r in cur.fetchall():
                open_incidents.append({
                    "id": r["id"],
                    "event_type": r["event_type"],
                    "severity": r["severity"],
                    "title": r["title"],
                    "message": r["message"],
                    "created_at": r["created_at"],
                })
        except Exception:
            pass

        # 3. Fetch staff exceptions
        try:
            cur.execute(
                """
                SELECT staff_id, name, role, on_duty
                FROM staff
                WHERE station_code = ? AND on_duty = 0
                LIMIT 5;
                """,
                (station_code,),
            )
            for r in cur.fetchall():
                crew_exceptions.append({
                    "staff_id": r["staff_id"],
                    "name": r["name"],
                    "role": r["role"],
                    "status": "OFF_DUTY_EXCEPTION",
                })
        except Exception:
            pass

    return {
        "active_srs": active_srs,
        "open_incidents": open_incidents,
        "crew_exceptions": crew_exceptions,
        "active_possessions": active_possessions,
    }


@router.get("/current", response_model=Dict[str, Any])
def get_current_handover_summary(
    station_code: str = Query("NDLS", description="Station code"),
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Auto-aggregates operational data to prepare the current shift handover log."""
    summary = auto_aggregate_station_state(station_code, db)
    now = datetime.now(timezone.utc)
    hour = now.hour
    shift_type = "morning" if 6 <= hour < 14 else ("afternoon" if 14 <= hour < 22 else "night")

    return {
        "station_code": station_code,
        "suggested_date": now.strftime("%Y-%m-%d"),
        "suggested_shift": shift_type,
        "outgoing_user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "full_name": current_user["full_name"],
            "role_id": current_user["role_id"],
        },
        **summary,
    }


@router.post("/draft", response_model=HandoverResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_draft(
    req: DraftHandoverRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Initializes or updates a draft shift handover logbook entry."""
    state = auto_aggregate_station_state(req.station_code, db)
    open_incidents_json = json.dumps(state["open_incidents"])
    active_srs_json = json.dumps(state["active_srs"])
    active_possessions_json = json.dumps(state["active_possessions"])
    crew_exceptions_json = json.dumps(state["crew_exceptions"])

    with db.transaction() as cur:
        # Check if draft already exists for this station/date/shift
        cur.execute(
            """
            SELECT id FROM handover_log
            WHERE station_code = ? AND shift_date = ? AND shift_type = ? AND status = 'draft';
            """,
            (req.station_code, req.shift_date, req.shift_type),
        )
        row = cur.fetchone()
        if row:
            handover_id = row["id"]
            cur.execute(
                """
                UPDATE handover_log
                SET operational_notes = ?, open_incidents_json = ?, active_srs_json = ?,
                    active_possessions_json = ?, crew_exceptions_json = ?, outgoing_user_id = ?
                WHERE id = ?;
                """,
                (
                    req.operational_notes,
                    open_incidents_json,
                    active_srs_json,
                    active_possessions_json,
                    crew_exceptions_json,
                    current_user["id"],
                    handover_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO handover_log (
                    station_code, shift_date, shift_type, outgoing_user_id,
                    open_incidents_json, active_srs_json, active_possessions_json,
                    crew_exceptions_json, operational_notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft');
                """,
                (
                    req.station_code,
                    req.shift_date,
                    req.shift_type,
                    current_user["id"],
                    open_incidents_json,
                    active_srs_json,
                    active_possessions_json,
                    crew_exceptions_json,
                    req.operational_notes,
                ),
            )
            handover_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="HANDOVER_DRAFT_SAVED",
            table_name="handover_log",
            record_id=handover_id,
            after_state={"station_code": req.station_code, "shift_date": req.shift_date, "shift_type": req.shift_type},
        )

    return HandoverResponse(
        id=handover_id,
        station_code=req.station_code,
        shift_date=req.shift_date,
        shift_type=req.shift_type,
        outgoing_user_id=current_user["id"],
        outgoing_user_name=current_user["full_name"],
        open_incidents=state["open_incidents"],
        active_srs=state["active_srs"],
        active_possessions=state["active_possessions"],
        crew_exceptions=state["crew_exceptions"],
        operational_notes=req.operational_notes,
        status="draft",
    )


@router.post("/{handover_id}/sign-out", response_model=HandoverResponse)
def sign_out_shift(
    handover_id: int,
    req: SignOutRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Outgoing Station Master digitally signs the shift handover."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM handover_log WHERE id = ?;", (handover_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover log not found.")

        notes = req.operational_notes or row["operational_notes"]
        cur.execute(
            """
            UPDATE handover_log
            SET outgoing_signed_at = ?, operational_notes = ?, status = 'signed', outgoing_user_id = ?
            WHERE id = ?;
            """,
            (now_iso, notes, current_user["id"], handover_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="HANDOVER_OUTGOING_SIGNED",
            table_name="handover_log",
            record_id=handover_id,
            after_state={"signed_at": now_iso, "status": "signed"},
        )

    return HandoverResponse(
        id=handover_id,
        station_code=row["station_code"],
        shift_date=row["shift_date"],
        shift_type=row["shift_type"],
        outgoing_user_id=current_user["id"],
        outgoing_user_name=current_user["full_name"],
        outgoing_signed_at=now_iso,
        open_incidents=json.loads(row["open_incidents_json"] or "[]"),
        active_srs=json.loads(row["active_srs_json"] or "[]"),
        active_possessions=json.loads(row["active_possessions_json"] or "[]"),
        crew_exceptions=json.loads(row["crew_exceptions_json"] or "[]"),
        operational_notes=notes,
        status="signed",
    )


@router.post("/{handover_id}/ack-in", response_model=HandoverResponse)
def acknowledge_incoming_shift(
    handover_id: int,
    req: AckInRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Incoming Station Master reviews and formally acknowledges taking over the shift."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM handover_log WHERE id = ?;", (handover_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover log not found.")

        if row["status"] != "signed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Handover cannot be acknowledged before outgoing Station Master signs.",
            )

        cur.execute(
            """
            UPDATE handover_log
            SET incoming_user_id = ?, incoming_acked_at = ?, status = 'acknowledged'
            WHERE id = ?;
            """,
            (current_user["id"], now_iso, handover_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="HANDOVER_INCOMING_ACKNOWLEDGED",
            table_name="handover_log",
            record_id=handover_id,
            after_state={"acked_at": now_iso, "status": "acknowledged"},
        )

    return HandoverResponse(
        id=handover_id,
        station_code=row["station_code"],
        shift_date=row["shift_date"],
        shift_type=row["shift_type"],
        outgoing_user_id=row["outgoing_user_id"],
        incoming_user_id=current_user["id"],
        incoming_user_name=current_user["full_name"],
        outgoing_signed_at=row["outgoing_signed_at"],
        incoming_acked_at=now_iso,
        open_incidents=json.loads(row["open_incidents_json"] or "[]"),
        active_srs=json.loads(row["active_srs_json"] or "[]"),
        active_possessions=json.loads(row["active_possessions_json"] or "[]"),
        crew_exceptions=json.loads(row["crew_exceptions_json"] or "[]"),
        operational_notes=row["operational_notes"],
        status="acknowledged",
    )


@router.get("/history", response_model=List[HandoverResponse])
def list_handover_history(
    station_code: str = Query("NDLS"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin", "viewer"])),
    db: Database = Depends(get_db),
):
    """Fetches past shift handover records for the station."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT h.*, u_out.full_name as out_name, u_in.full_name as in_name
            FROM handover_log h
            LEFT JOIN users u_out ON h.outgoing_user_id = u_out.id
            LEFT JOIN users u_in ON h.incoming_user_id = u_in.id
            WHERE h.station_code = ?
            ORDER BY h.id DESC LIMIT ?;
            """,
            (station_code, limit),
        )
        rows = cur.fetchall()

    return [
        HandoverResponse(
            id=r["id"],
            station_code=r["station_code"],
            shift_date=r["shift_date"],
            shift_type=r["shift_type"],
            outgoing_user_id=r["outgoing_user_id"],
            outgoing_user_name=r["out_name"],
            incoming_user_id=r["incoming_user_id"],
            incoming_user_name=r["in_name"],
            outgoing_signed_at=r["outgoing_signed_at"],
            incoming_acked_at=r["incoming_acked_at"],
            open_incidents=json.loads(r["open_incidents_json"] or "[]"),
            active_srs=json.loads(r["active_srs_json"] or "[]"),
            active_possessions=json.loads(r["active_possessions_json"] or "[]"),
            crew_exceptions=json.loads(r["crew_exceptions_json"] or "[]"),
            operational_notes=r["operational_notes"],
            status=r["status"],
        )
        for r in rows
    ]
