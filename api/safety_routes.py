"""RailTwin-X Safety & Compliance Master Routes (Phase 2 - Modules D2, D3, D4, D5, D6).

Provides:
- D2: Caution Orders / Speed Restrictions (TSR) Registry
- D3: Permit-to-Work / Track Possessions Workflow
- D4: Incident & Near-Miss Register
- D5: SOP / Emergency Checklist Runner with Multi-Channel Alert Dispatch
- D6: Level Crossing (LC) Status Board
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

router = APIRouter(prefix="/api/safety", tags=["Safety & Compliance (Phase 2)"])


# ----------------------------------------------------
# D2. CAUTION ORDERS / SPEED RESTRICTIONS (TSR)
# ----------------------------------------------------
class SpeedRestrictionCreate(BaseModel):
    from_code: str = Field(..., description="From station code")
    to_code: str = Field(..., description="To station code")
    start_km: float = 0.0
    end_km: float = 0.0
    speed_limit_kmph: int = Field(..., ge=10, le=160, description="Restricted speed in km/h")
    cause: str = Field(..., description="Reason e.g. Track renewal, deep screening")
    permanent_or_temp: str = Field("TEMPORARY", description="TEMPORARY or PERMANENT")
    effective_from: str = Field(..., description="ISO date or timestamp")
    effective_to: Optional[str] = None


@router.post("/tsr", response_model=Dict[str, Any])
def create_speed_restriction(
    req: SpeedRestrictionCreate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Issues a new Caution Order / Speed Restriction on a block section."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO speed_restrictions (
                from_code, to_code, start_km, end_km, speed_limit_kmph,
                cause, permanent_or_temp, effective_from, effective_to,
                status, issued_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?);
            """,
            (
                req.from_code.upper(),
                req.to_code.upper(),
                req.start_km,
                req.end_km,
                req.speed_limit_kmph,
                req.cause,
                req.permanent_or_temp.upper(),
                req.effective_from,
                req.effective_to,
                current_user["id"],
                now_iso,
            ),
        )
        tsr_id = cur.lastrowid

        # Update block status to CAUTION
        block_id = f"BLK-{req.from_code.upper()}-{req.to_code.upper()}"
        cur.execute(
            """
            INSERT INTO block_status (block_id, from_code, to_code, state, since, notes)
            VALUES (?, ?, ?, 'CAUTION', ?, ?)
            ON CONFLICT(block_id) DO UPDATE SET
                state = CASE WHEN block_status.state != 'OCCUPIED' THEN 'CAUTION' ELSE block_status.state END,
                notes = excluded.notes;
            """,
            (block_id, req.from_code.upper(), req.to_code.upper(), now_iso, f"TSR {req.speed_limit_kmph} km/h: {req.cause}"),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TSR_ISSUED",
            table_name="speed_restrictions",
            record_id=str(tsr_id),
            after_state={"speed_limit": req.speed_limit_kmph, "section": f"{req.from_code}-{req.to_code}", "cause": req.cause},
        )

    # Notify section staff
    notify(
        event_type="TSR_ISSUED",
        target_roles=["station_master", "dy_sm", "section_controller", "loco_pilot", "guard"],
        severity="warn",
        title=f"Caution Order: {req.speed_limit_kmph} km/h on {req.from_code}-{req.to_code}",
        message=f"TSR #{tsr_id} active on {req.from_code}-{req.to_code} ({req.start_km}km-{req.end_km}km): {req.cause}.",
        payload={"tsr_id": tsr_id, "speed_limit": req.speed_limit_kmph},
        db=db,
    )

    return {"id": tsr_id, "status": "ACTIVE", "speed_limit_kmph": req.speed_limit_kmph, "created_at": now_iso}


@router.get("/tsr", response_model=List[Dict[str, Any]])
def list_speed_restrictions(
    station_code: Optional[str] = Query(None, description="Filter by station code"),
    status: Optional[str] = Query("ACTIVE", description="ACTIVE, CANCELLED, or ALL"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists all active and historical Caution Orders."""
    with db.transaction() as cur:
        query = "SELECT * FROM speed_restrictions WHERE 1=1"
        params: List[Any] = []
        if status and status.upper() != "ALL":
            query += " AND status = ?"
            params.append(status.upper())
        if station_code:
            query += " AND (from_code = ? OR to_code = ?)"
            params.extend([station_code.upper(), station_code.upper()])
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


@router.delete("/tsr/{tsr_id}", response_model=Dict[str, Any])
def cancel_speed_restriction(
    tsr_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Cancels/lifts an active Speed Restriction."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM speed_restrictions WHERE id = ?;", (tsr_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Caution order not found.")

        cur.execute("UPDATE speed_restrictions SET status = 'CANCELLED' WHERE id = ?;", (tsr_id,))

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TSR_CANCELLED",
            table_name="speed_restrictions",
            record_id=str(tsr_id),
            before_state=dict(row),
            after_state={"status": "CANCELLED"},
        )

    return {"id": tsr_id, "status": "CANCELLED", "cancelled_at": now_iso}


# ----------------------------------------------------
# D3. PERMIT-TO-WORK / TRACK POSSESSIONS
# ----------------------------------------------------
class PossessionRequest(BaseModel):
    possession_type: str = Field(..., description="BLOCK_SECTION, PLATFORM, OHE_LINE, YARD_TRACK")
    element_id: str = Field(..., description="e.g. BLK-NDLS-GZB or PF-NDLS-1")
    station_code: str
    start_time: str
    end_time: str
    work_type: str = Field("P_WAY", description="P_WAY, OHE_TRACTION, S_AND_T, BRIDGE_WORK, GENERAL")
    requesting_dept: str
    notes: Optional[str] = None


@router.post("/possession/request", response_model=Dict[str, Any])
def request_possession(
    req: PossessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Submits a Permit-to-Work / Track Possession request."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO possessions (
                possession_type, element_id, station_code, start_time, end_time,
                work_type, requesting_dept, status, notes, created_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'REQUESTED', ?, ?, ?);
            """,
            (
                req.possession_type.upper(),
                req.element_id,
                req.station_code.upper(),
                req.start_time,
                req.end_time,
                req.work_type.upper(),
                req.requesting_dept,
                req.notes,
                current_user["id"],
                now_iso,
            ),
        )
        p_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="POSSESSION_REQUESTED",
            table_name="possessions",
            record_id=str(p_id),
            after_state={"element_id": req.element_id, "window": f"{req.start_time}-{req.end_time}"},
        )

    return {"id": p_id, "status": "REQUESTED", "element_id": req.element_id, "created_at": now_iso}


@router.post("/possession/{possession_id}/grant", response_model=Dict[str, Any])
def grant_possession(
    possession_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Station Master / Controller authorizes and activates a Track Possession."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM possessions WHERE id = ?;", (possession_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Possession not found.")
        if row["status"] not in ("REQUESTED", "GRANTED"):
            raise HTTPException(status_code=400, detail=f"Cannot grant possession with status {row['status']}.")

        cur.execute(
            """
            UPDATE possessions
            SET status = 'ACTIVE', granted_by = ?, granted_at = ?
            WHERE id = ?;
            """,
            (current_user["id"], now_iso, possession_id),
        )

        # Automatically block corresponding infrastructure
        p_type = row["possession_type"]
        elem_id = row["element_id"]
        stn = row["station_code"]

        if p_type == "PLATFORM":
            try:
                pf_num = int(elem_id.replace(f"PF-{stn}-", "").replace("PF", ""))
                cur.execute(
                    """
                    INSERT INTO platform_states (station_code, platform_number, state, occupied_since, notes)
                    VALUES (?, ?, 'BLOCKED_MAINT', ?, ?)
                    ON CONFLICT(station_code, platform_number) DO UPDATE SET
                        state = 'BLOCKED_MAINT',
                        occupied_since = excluded.occupied_since,
                        notes = excluded.notes;
                    """,
                    (stn, pf_num, now_iso, f"Possession #{possession_id}: {row['work_type']}"),
                )
            except Exception:
                pass
        elif p_type == "BLOCK_SECTION":
            cur.execute(
                """
                UPDATE block_status
                SET state = 'BLOCKED', notes = ?
                WHERE block_id = ?;
                """,
                (f"Possession #{possession_id} Active", elem_id),
            )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="POSSESSION_GRANTED",
            table_name="possessions",
            record_id=str(possession_id),
            after_state={"status": "ACTIVE", "granted_by": current_user["id"]},
        )

    # Notify maintenance & traffic teams
    notify(
        event_type="POSSESSION_GRANTED",
        target_roles=["station_master", "dy_sm", "section_controller", "viewer"],
        severity="warn",
        title=f"Track Possession Active: {row['element_id']}",
        message=f"Possession #{possession_id} ({row['work_type']}) granted on {row['element_id']} by {current_user['full_name']}.",
        payload={"possession_id": possession_id, "element_id": row["element_id"]},
        db=db,
    )

    return {"id": possession_id, "status": "ACTIVE", "granted_by": current_user["id"], "granted_at": now_iso}


@router.post("/possession/{possession_id}/restore", response_model=Dict[str, Any])
def restore_possession(
    possession_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Completes work and restores track/platform to normal revenue operations."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM possessions WHERE id = ?;", (possession_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Possession not found.")

        cur.execute(
            """
            UPDATE possessions
            SET status = 'RESTORED', restored_by = ?, restored_at = ?
            WHERE id = ?;
            """,
            (current_user["id"], now_iso, possession_id),
        )

        # Restore infrastructure
        p_type = row["possession_type"]
        elem_id = row["element_id"]
        stn = row["station_code"]

        if p_type == "PLATFORM":
            try:
                pf_num = int(elem_id.replace(f"PF-{stn}-", "").replace("PF", ""))
                cur.execute(
                    """
                    UPDATE platform_states
                    SET state = 'FREE', occupied_by_train = NULL, notes = 'Restored from maintenance'
                    WHERE station_code = ? AND platform_number = ?;
                    """,
                    (stn, pf_num),
                )
            except Exception:
                pass
        elif p_type == "BLOCK_SECTION":
            cur.execute(
                """
                UPDATE block_status
                SET state = 'CLEAR', notes = 'Restored from maintenance'
                WHERE block_id = ?;
                """,
                (elem_id,),
            )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="POSSESSION_RESTORED",
            table_name="possessions",
            record_id=str(possession_id),
            after_state={"status": "RESTORED", "restored_by": current_user["id"]},
        )

    return {"id": possession_id, "status": "RESTORED", "restored_at": now_iso}


@router.get("/possessions", response_model=List[Dict[str, Any]])
def list_possessions(
    station_code: Optional[str] = Query(None, description="Station filter"),
    status: Optional[str] = Query(None, description="REQUESTED, ACTIVE, RESTORED"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists track possessions with status and station filters."""
    with db.transaction() as cur:
        query = "SELECT * FROM possessions WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        if status:
            query += " AND status = ?"
            params.append(status.upper())
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


# ----------------------------------------------------
# D4. INCIDENT & NEAR-MISS REGISTER
# ----------------------------------------------------
class IncidentReportCreate(BaseModel):
    incident_type: str = Field(..., description="SPAD, DERAILMENT, EQUIPMENT_FAIL, NEAR_MISS, GATE_BURST, OHE_BREAKDOWN, TRESPASSING")
    severity: str = Field(..., description="MINOR, MAJOR, CRITICAL")
    station_code: str
    location_km: Optional[float] = None
    train_no: Optional[str] = None
    summary: str
    action_taken: Optional[str] = None


@router.post("/incidents", response_model=Dict[str, Any])
def report_incident(
    req: IncidentReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Logs a safety incident or near-miss event with immediate multi-role escalation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO incidents (
                incident_type, severity, station_code, location_km,
                train_no, summary, investigation_status, action_taken,
                reported_by, reported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?);
            """,
            (
                req.incident_type.upper(),
                req.severity.upper(),
                req.station_code.upper(),
                req.location_km,
                req.train_no,
                req.summary,
                req.action_taken,
                current_user["id"],
                now_iso,
            ),
        )
        inc_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="INCIDENT_REPORTED",
            table_name="incidents",
            record_id=str(inc_id),
            after_state={"type": req.incident_type, "severity": req.severity, "summary": req.summary},
        )

    # Trigger emergency notification
    notify(
        event_type="INCIDENT_REPORTED",
        target_roles=["station_master", "dy_sm", "section_controller", "admin"],
        severity="critical" if req.severity.upper() == "CRITICAL" else "warn",
        title=f"🚨 SAFETY INCIDENT: {req.incident_type} ({req.severity}) at {req.station_code}",
        message=f"Incident #{inc_id} reported at {req.station_code}: {req.summary}. Train: {req.train_no or 'N/A'}.",
        payload={"incident_id": inc_id, "severity": req.severity, "type": req.incident_type},
        db=db,
    )

    return {"id": inc_id, "status": "OPEN", "severity": req.severity, "reported_at": now_iso}


@router.get("/incidents", response_model=List[Dict[str, Any]])
def list_incidents(
    station_code: Optional[str] = Query(None, description="Station filter"),
    investigation_status: Optional[str] = Query(None, description="OPEN, UNDER_REVIEW, CLOSED"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists safety incidents in the digital register."""
    with db.transaction() as cur:
        query = "SELECT * FROM incidents WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        if investigation_status:
            query += " AND investigation_status = ?"
            params.append(investigation_status.upper())
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


# ----------------------------------------------------
# D5. SOP / EMERGENCY CHECKLIST RUNNER
# ----------------------------------------------------
SOP_TEMPLATES = [
    {
        "template_id": "SOP-SPAD-01",
        "title": "SPAD (Signal Passed at Danger) Emergency Protocol",
        "severity": "CRITICAL",
        "steps": [
            "1. Immediately transmit Emergency Stop message on All-Station VHF channel (161.150 MHz).",
            "2. Trip OHE power supply for the affected section via Section Controller / TPC.",
            "3. Place Red Banner Flags and 3 detonators 10 meters apart at 1200m distance from fouling point.",
            "4. Confiscate Loco Pilot & Guard breathalyzer samples and log in Master Register.",
            "5. Secure Joint Observation Report signed by SM, TI, and SE (Signals).",
        ],
    },
    {
        "template_id": "SOP-OHE-02",
        "title": "OHE Traction Power Failure & Catenary Sag Protocol",
        "severity": "MAJOR",
        "steps": [
            "1. Log exact tripping time and sub-station breaker indicator (Zone 1 / Zone 2).",
            "2. Section Controller halts incoming electric rakes at adjacent block stations.",
            "3. Tower Wagon (OHE inspection car) requisitioned from nearest depot.",
            "4. Issue Caution Order (TSR 30 km/h or Neutral Section Coasting) if coasting permitted.",
            "5. Secure Power Block & Earth before allowing linesmen on track.",
        ],
    },
    {
        "template_id": "SOP-FOG-03",
        "title": "Monsoon / Dense Fog Visibility Operations Protocol",
        "severity": "MAJOR",
        "steps": [
            "1. Verify Visibility Test Object (VTO) is obscured at 180 meters.",
            "2. Distribute Fog Signal Detonators to designated Fog Signalmen at Warner / Distant signals.",
            "3. Restrict Maximum Permissible Speed (MPS) to 75 km/h for all Express trains.",
            "4. Ensure all locomotive Flasher Lights and High-Intensity LEDs are functional.",
        ],
    },
]


@router.get("/sop/templates", response_model=List[Dict[str, Any]])
def get_sop_templates():
    """Returns available Indian Railways standard emergency response SOP templates."""
    return SOP_TEMPLATES


class StartSOPRequest(BaseModel):
    template_id: str
    station_code: str


@router.post("/sop/start", response_model=Dict[str, Any])
def start_sop_run(
    req: StartSOPRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Initiates an active emergency checklist run and alerts on-duty staff."""
    template = next((t for t in SOP_TEMPLATES if t["template_id"] == req.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="SOP template not found.")

    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO sop_runs (
                template_id, title, station_code, severity, status,
                steps_completed_json, started_by, started_at
            )
            VALUES (?, ?, ?, ?, 'IN_PROGRESS', '[]', ?, ?);
            """,
            (template["template_id"], template["title"], req.station_code.upper(), template["severity"], current_user["id"], now_iso),
        )
        run_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="SOP_STARTED",
            table_name="sop_runs",
            record_id=str(run_id),
            after_state={"template": req.template_id, "title": template["title"]},
        )

    # Multi-role emergency alert
    notify(
        event_type="SOP_TRIGGERED",
        target_roles=["station_master", "dy_sm", "section_controller", "loco_pilot", "guard", "admin"],
        severity="critical" if template["severity"] == "CRITICAL" else "warn",
        title=f"⚡ EMERGENCY SOP RUNNING: {template['title']}",
        message=f"Emergency SOP #{run_id} initiated at {req.station_code} by {current_user['full_name']}. Follow checklist immediately.",
        payload={"run_id": run_id, "template_id": req.template_id},
        db=db,
    )

    return {
        "run_id": run_id,
        "template_id": template["template_id"],
        "title": template["title"],
        "status": "IN_PROGRESS",
        "started_at": now_iso,
        "steps": template["steps"],
    }


class CompleteStepRequest(BaseModel):
    step_index: int


@router.post("/sop/{run_id}/step", response_model=Dict[str, Any])
def complete_sop_step(
    run_id: int,
    req: CompleteStepRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Marks a checklist step as completed with actor ID and ISO timestamp."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM sop_runs WHERE id = ?;", (run_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="SOP run not found.")

        completed_steps = json.loads(row["steps_completed_json"])
        completed_steps.append({
            "step_index": req.step_index,
            "completed_by": current_user["id"],
            "completed_at": now_iso,
        })

        # Check template total steps
        template = next((t for t in SOP_TEMPLATES if t["template_id"] == row["template_id"]), None)
        total_steps = len(template["steps"]) if template else 5
        is_finished = len(completed_steps) >= total_steps

        new_status = "COMPLETED" if is_finished else "IN_PROGRESS"
        comp_time = now_iso if is_finished else None

        cur.execute(
            """
            UPDATE sop_runs
            SET steps_completed_json = ?, status = ?, completed_at = ?
            WHERE id = ?;
            """,
            (json.dumps(completed_steps), new_status, comp_time, run_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="SOP_STEP_COMPLETED",
            table_name="sop_runs",
            record_id=str(run_id),
            after_state={"step": req.step_index, "status": new_status},
        )

    return {
        "run_id": run_id,
        "step_index": req.step_index,
        "total_completed": len(completed_steps),
        "status": new_status,
        "completed_at": now_iso,
    }


@router.get("/sop/active", response_model=List[Dict[str, Any]])
def list_active_sop_runs(
    station_code: Optional[str] = Query(None, description="Station filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists ongoing emergency SOP checklist runs."""
    with db.transaction() as cur:
        query = "SELECT * FROM sop_runs WHERE status = 'IN_PROGRESS'"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["steps_completed"] = json.loads(r["steps_completed_json"])
    return rows


# ----------------------------------------------------
# D6. LEVEL CROSSING (LC) STATUS BOARD
# ----------------------------------------------------
class LCStatusUpdate(BaseModel):
    status: str = Field(..., description="NORMAL, DEFECTIVE, BOOM_DAMAGED, INTERLOCK_FAIL, MAINTENANCE")
    notes: Optional[str] = None


@router.get("/lc/status", response_model=List[Dict[str, Any]])
def list_level_crossings(
    station_code: Optional[str] = Query(None, description="Station filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists Level Crossings and their real-time operational status."""
    with db.transaction() as cur:
        # Seed default sample LCs if table is empty
        cur.execute("SELECT COUNT(*) as count FROM level_crossings;")
        c = cur.fetchone()["count"]
        if c == 0:
            sample_lcs = [
                ("LC-102", "NDLS", 2.4, "MANNED_INTERLOCKED", "NORMAL", "2026-08-28T06:00:00Z", "Ram Swaroop", "+919876543210"),
                ("LC-105", "NDLS", 5.8, "MANNED_INTERLOCKED", "NORMAL", "2026-08-28T06:00:00Z", "Kishan Lal", "+919876543211"),
                ("LC-118", "GZB", 18.2, "SPECIAL_CLASS", "NORMAL", "2026-08-28T06:00:00Z", "Suraj Bhan", "+919876543212"),
                ("LC-124", "ALJN", 45.1, "MANNED_NON_INTERLOCKED", "DEFECTIVE", "2026-08-28T06:00:00Z", "Mahesh Kumar", "+919876543213"),
            ]
            for lc in sample_lcs:
                cur.execute(
                    """
                    INSERT INTO level_crossings (
                        lc_number, station_code, km, gate_type, status,
                        last_inspected, gateman_name, contact_phone
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    lc,
                )

        query = "SELECT * FROM level_crossings WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        query += " ORDER BY km ASC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


@router.put("/lc/{lc_id}/status", response_model=Dict[str, Any])
def update_lc_status(
    lc_id: int,
    req: LCStatusUpdate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Updates level crossing operational state."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM level_crossings WHERE id = ?;", (lc_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Level crossing not found.")

        cur.execute(
            """
            UPDATE level_crossings
            SET status = ?, notes = ?, last_inspected = ?
            WHERE id = ?;
            """,
            (req.status.upper(), req.notes, now_iso, lc_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="LC_STATUS_UPDATED",
            table_name="level_crossings",
            record_id=str(lc_id),
            before_state=dict(row),
            after_state={"status": req.status.upper(), "notes": req.notes},
        )

    # Notify if defective
    if req.status.upper() in ("DEFECTIVE", "BOOM_DAMAGED", "INTERLOCK_FAIL"):
        notify(
            event_type="LC_DEFECTIVE",
            target_roles=["station_master", "dy_sm", "section_controller", "loco_pilot"],
            severity="critical",
            title=f"🚨 LC GATE DEFECTIVE: {row['lc_number']} (Km {row['km']})",
            message=f"Gate {row['lc_number']} at {row['station_code']} reported {req.status.upper()}. Issue Caution Order (TSR 20 km/h whistling).",
            payload={"lc_id": lc_id, "status": req.status.upper()},
            db=db,
        )

    return {"id": lc_id, "status": req.status.upper(), "updated_at": now_iso}
