"""RailTwin-X Workforce & Crew Intelligence API (Phase 4 - Modules F1, F2, F3, F4).

Provides:
- F1: Digital Breathalyzer Test Register & Zero-Tolerance Safety Interlock
- F2: Crew Management System (CMS) Rest & HOA Duty Breach Engine
- F3: Station Staff Shift Roster & Leave Tracking
- F4: Sahayak (Licensed Porter) Directory & Tariff Enforcement
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import get_current_user, require_role
from data.audit import record_audit
from data.db import Database, get_db
from notifications.dispatcher import notify

router = APIRouter(prefix="/api/workforce", tags=["Workforce & Crew Intelligence (Phase 4)"])


# ----------------------------------------------------
# F1. DIGITAL BREATHALYZER TEST REGISTER (ZERO TOLERANCE)
# ----------------------------------------------------
class BreathalyzerTestCreate(BaseModel):
    staff_id: str
    staff_name: str
    role: str = Field("loco_pilot", description="loco_pilot, alp, guard, station_master, shunter")
    train_no: Optional[str] = None
    duty_type: str = Field("SIGN_ON", description="SIGN_ON, SIGN_OFF, SURPRISE_CHECK")
    reading_mg_100ml: float = Field(0.0, ge=0.0, description="Alcohol reading in mg/100ml BAC")
    notes: Optional[str] = None


@router.post("/breathalyzer", response_model=Dict[str, Any])
def record_breathalyzer_test(
    req: BreathalyzerTestCreate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "crew_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Logs a Digital Breathalyzer test. Zero tolerance: Any reading > 0.00 triggers immediate duty lock and emergency alert."""
    now_iso = datetime.now(timezone.utc).isoformat()
    passed = 1 if req.reading_mg_100ml <= 0.00 else 0

    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO breathalyzer_tests (
                staff_id, staff_name, role, train_no, duty_type,
                reading_mg_100ml, passed, verified_by, test_time, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                req.staff_id,
                req.staff_name,
                req.role.lower(),
                req.train_no,
                req.duty_type.upper(),
                req.reading_mg_100ml,
                passed,
                current_user["id"],
                now_iso,
                req.notes,
            ),
        )
        test_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="BREATHALYZER_TEST_LOGGED",
            table_name="breathalyzer_tests",
            record_id=str(test_id),
            after_state={"staff": req.staff_name, "reading": req.reading_mg_100ml, "passed": passed},
        )

    # If test failed, dispatch urgent safety interlock alarm
    if passed == 0:
        notify(
            event_type="BREATHALYZER_FAILED",
            target_roles=["station_master", "dy_sm", "crew_controller", "section_controller", "admin"],
            severity="critical",
            title=f"🚨 BREATHALYZER POSITIVE: {req.staff_name} ({req.role.upper()})",
            message=(
                f"Zero Tolerance Interlock: {req.staff_name} ({req.role}) tested positive "
                f"({req.reading_mg_100ml} mg/100ml) for Train #{req.train_no or 'N/A'}. "
                f"Crew member LOCKED OUT. Immediate replacement mandatory."
            ),
            payload={"staff_id": req.staff_id, "reading": req.reading_mg_100ml, "train_no": req.train_no},
            db=db,
        )

    return {
        "id": test_id,
        "staff_id": req.staff_id,
        "staff_name": req.staff_name,
        "passed": bool(passed),
        "reading_mg_100ml": req.reading_mg_100ml,
        "verified_by": current_user["id"],
        "test_time": now_iso,
        "interlock_locked": (passed == 0),
    }


@router.get("/breathalyzer", response_model=List[Dict[str, Any]])
def list_breathalyzer_tests(
    failed_only: bool = Query(False, description="Filter for failed tests only"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists recent breathalyzer test records."""
    with db.transaction() as cur:
        query = "SELECT * FROM breathalyzer_tests WHERE 1=1"
        if failed_only:
            query += " AND passed = 0"
        query += " ORDER BY id DESC LIMIT 100;"
        cur.execute(query)
        rows = [dict(r) for r in cur.fetchall()]
    return rows


# ----------------------------------------------------
# F2. CREW CMS ROSTERS & HOURS OF ATTENDANCE (HOA)
# ----------------------------------------------------
class CrewSignOnRequest(BaseModel):
    crew_id: str
    staff_name: str
    role: str = Field("loco_pilot", description="loco_pilot, alp, guard")
    train_no: str
    station_code: str = "NDLS"
    duty_hours_limit: float = 10.0


@router.post("/crew/sign-on", response_model=Dict[str, Any])
def crew_sign_on(
    req: CrewSignOnRequest,
    current_user: Dict[str, Any] = Depends(require_role(["crew_controller", "station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Signs on train running crew (Loco Pilot, ALP, Guard) and starts duty hours tracking."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        # Check latest breathalyzer pass
        cur.execute(
            """
            SELECT passed, reading_mg_100ml
            FROM breathalyzer_tests
            WHERE staff_id = ?
            ORDER BY id DESC LIMIT 1;
            """,
            (req.crew_id,),
        )
        ba_row = cur.fetchone()
        if ba_row and ba_row["passed"] == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot Sign-On: Crew member has active Positive Breathalyzer Lock ({ba_row['reading_mg_100ml']} mg/100ml).",
            )

        cur.execute(
            """
            INSERT INTO crew_rosters (
                crew_id, staff_name, role, train_no, station_code,
                sign_on_time, duty_hours_limit, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ON_DUTY', ?);
            """,
            (
                req.crew_id,
                req.staff_name,
                req.role.lower(),
                req.train_no,
                req.station_code.upper(),
                now_iso,
                req.duty_hours_limit,
                now_iso,
            ),
        )
        roster_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="CREW_SIGN_ON",
            table_name="crew_rosters",
            record_id=str(roster_id),
            after_state={"crew": req.staff_name, "train_no": req.train_no, "sign_on": now_iso},
        )

    return {"id": roster_id, "crew_id": req.crew_id, "status": "ON_DUTY", "sign_on_time": now_iso}


@router.post("/crew/{roster_id}/sign-off", response_model=Dict[str, Any])
def crew_sign_off(
    roster_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["crew_controller", "station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Signs off running crew, calculates exact duty duration, and sets required rest period."""
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    with db.transaction() as cur:
        cur.execute("SELECT * FROM crew_rosters WHERE id = ?;", (roster_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Crew roster record not found.")

        sign_on_dt = datetime.fromisoformat(row["sign_on_time"].replace("Z", "+00:00"))
        duration_hours = (now_dt - sign_on_dt).total_seconds() / 3600.0

        # IR Rule: >= 8h duty requires 16h HQ rest; < 8h duty requires 12h HQ rest
        rest_due = 16.0 if duration_hours >= 8.0 else 12.0

        cur.execute(
            """
            UPDATE crew_rosters
            SET sign_off_time = ?, rest_hours_due = ?, status = 'RESTING'
            WHERE id = ?;
            """,
            (now_iso, rest_due, roster_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="CREW_SIGN_OFF",
            table_name="crew_rosters",
            record_id=str(roster_id),
            after_state={"duty_hours": round(duration_hours, 2), "rest_due": rest_due},
        )

    return {
        "id": roster_id,
        "crew_id": row["crew_id"],
        "status": "RESTING",
        "duty_hours": round(duration_hours, 2),
        "rest_hours_due": rest_due,
        "sign_off_time": now_iso,
    }


@router.get("/crew/roster", response_model=List[Dict[str, Any]])
def list_crew_roster(
    station_code: Optional[str] = Query(None, description="Station filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists current crew roster with elapsed duty hours."""
    now_dt = datetime.now(timezone.utc)
    with db.transaction() as cur:
        # Seed default sample crew if empty
        cur.execute("SELECT COUNT(*) as count FROM crew_rosters;")
        c = cur.fetchone()["count"]
        if c == 0:
            now_iso = now_dt.isoformat()
            sample_crew = [
                ("CRW-LP-101", "Virender Singh", "loco_pilot", "12004", "NDLS", now_iso, 10.0, "ON_DUTY", now_iso),
                ("CRW-ALP-102", "Suresh Kumar", "alp", "12004", "NDLS", now_iso, 10.0, "ON_DUTY", now_iso),
                ("CRW-GD-103", "Anil Meena", "guard", "12004", "NDLS", now_iso, 10.0, "ON_DUTY", now_iso),
                ("CRW-LP-104", "Rajesh Sharma", "loco_pilot", "12424", "NDLS", now_iso, 10.0, "ON_DUTY", now_iso),
            ]
            for cr in sample_crew:
                cur.execute(
                    """
                    INSERT INTO crew_rosters (
                        crew_id, staff_name, role, train_no, station_code,
                        sign_on_time, duty_hours_limit, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    cr,
                )

        query = "SELECT * FROM crew_rosters WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]

    for r in rows:
        if r["status"] == "ON_DUTY":
            try:
                son = datetime.fromisoformat(r["sign_on_time"].replace("Z", "+00:00"))
                elapsed = (now_dt - son).total_seconds() / 3600.0
                r["elapsed_duty_hours"] = round(elapsed, 2)
                r["hours_remaining"] = round(max(0.0, r["duty_hours_limit"] - elapsed), 2)
                r["is_near_breach"] = elapsed >= (r["duty_hours_limit"] - 2.0)
            except Exception:
                r["elapsed_duty_hours"] = 0.0
                r["hours_remaining"] = 10.0
                r["is_near_breach"] = False
        else:
            r["elapsed_duty_hours"] = 0.0
            r["hours_remaining"] = 0.0
            r["is_near_breach"] = False

    return rows


@router.get("/crew/breaches", response_model=List[Dict[str, Any]])
def check_crew_breaches(
    station_code: Optional[str] = Query(None, description="Station filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Detects crew approaching or exceeding the 10-hour duty limit (or 14-hour HOA)."""
    all_crew = list_crew_roster(station_code=station_code, current_user=current_user, db=db)
    breaches = [c for c in all_crew if c.get("is_near_breach") or c.get("elapsed_duty_hours", 0) > c.get("duty_hours_limit", 10)]
    return breaches


# ----------------------------------------------------
# F3. STATION STAFF SHIFT SCHEDULER
# ----------------------------------------------------
class ShiftAssignmentCreate(BaseModel):
    staff_id: str
    staff_name: str
    role_id: str
    station_code: str = "NDLS"
    shift_date: str
    shift_type: str = Field("morning", description="morning, afternoon, night")


@router.post("/shifts", response_model=Dict[str, Any])
def assign_staff_shift(
    req: ShiftAssignmentCreate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "admin"])),
    db: Database = Depends(get_db),
):
    """Assigns station staff to an operational shift."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO staff_shifts (
                staff_id, staff_name, role_id, station_code,
                shift_date, shift_type, attendance_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'PRESENT', ?);
            """,
            (
                req.staff_id,
                req.staff_name,
                req.role_id,
                req.station_code.upper(),
                req.shift_date,
                req.shift_type.lower(),
                now_iso,
            ),
        )
        s_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="STAFF_SHIFT_ASSIGNED",
            table_name="staff_shifts",
            record_id=str(s_id),
            after_state={"staff": req.staff_name, "shift": f"{req.shift_date} {req.shift_type}"},
        )

    return {"id": s_id, "staff_name": req.staff_name, "shift_date": req.shift_date, "shift_type": req.shift_type}


@router.get("/shifts", response_model=List[Dict[str, Any]])
def list_staff_shifts(
    station_code: Optional[str] = Query(None, description="Station filter"),
    shift_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists staff shift roster."""
    with db.transaction() as cur:
        # Seed default sample shifts if empty
        cur.execute("SELECT COUNT(*) as count FROM staff_shifts;")
        c = cur.fetchone()["count"]
        if c == 0:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            now_iso = datetime.now(timezone.utc).isoformat()
            sample_shifts = [
                ("usr-sm-ndls-01", "Station Master Day", "station_master", "NDLS", today_str, "morning", "PRESENT", now_iso),
                ("usr-dysm-01", "Dy. Station Master Morning", "dy_sm", "NDLS", today_str, "morning", "PRESENT", now_iso),
                ("usr-section-ctrl-01", "Section Controller Main", "section_controller", "NDLS", today_str, "morning", "PRESENT", now_iso),
                ("usr-crew-ctrl-01", "Crew Controller Day", "crew_controller", "NDLS", today_str, "morning", "PRESENT", now_iso),
            ]
            for s in sample_shifts:
                cur.execute(
                    """
                    INSERT INTO staff_shifts (
                        staff_id, staff_name, role_id, station_code,
                        shift_date, shift_type, attendance_status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    s,
                )

        query = "SELECT * FROM staff_shifts WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        if shift_date:
            query += " AND shift_date = ?"
            params.append(shift_date)
        query += " ORDER BY shift_date DESC, id ASC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


# ----------------------------------------------------
# F4. SAHAYAK (LICENSED PORTER) DIRECTORY & TARIFF
# ----------------------------------------------------
@router.get("/sahayak", response_model=List[Dict[str, Any]])
def list_sahayak_roster(
    station_code: Optional[str] = Query(None, description="Station filter"),
    on_duty_only: bool = Query(False, description="Filter on-duty only"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists registered Sahayak (licensed porters) and their platform allocations."""
    with db.transaction() as cur:
        # Seed default sample sahayak if empty
        cur.execute("SELECT COUNT(*) as count FROM sahayak_roster;")
        c = cur.fetchone()["count"]
        if c == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            sample_sahayaks = [
                ("COOLIE-101", "Ram Charan", "+919876543201", "NDLS", 1, "morning", 1, 150.0, now_iso),
                ("COOLIE-102", "Mohan Lal", "+919876543202", "NDLS", 1, "morning", 1, 150.0, now_iso),
                ("COOLIE-103", "Jagdish Prasad", "+919876543203", "NDLS", 2, "morning", 1, 150.0, now_iso),
                ("COOLIE-104", "Dharmendra Yadav", "+919876543204", "NDLS", 3, "morning", 1, 150.0, now_iso),
                ("COOLIE-105", "Rameshwar Dayal", "+919876543205", "NDLS", 4, "morning", 1, 150.0, now_iso),
            ]
            for sk in sample_sahayaks:
                cur.execute(
                    """
                    INSERT INTO sahayak_roster (
                        badge_number, name, phone, station_code, assigned_platform,
                        shift, on_duty, tariff_fixed_inr, last_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    sk,
                )

        query = "SELECT * FROM sahayak_roster WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        if on_duty_only:
            query += " AND on_duty = 1"
        query += " ORDER BY assigned_platform ASC, badge_number ASC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


@router.put("/sahayak/{sahayak_id}/duty", response_model=Dict[str, Any])
def toggle_sahayak_duty(
    sahayak_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "commercial_inspector", "admin"])),
    db: Database = Depends(get_db),
):
    """Toggles Sahayak on-duty / off-duty status."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM sahayak_roster WHERE id = ?;", (sahayak_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sahayak record not found.")

        new_duty = 0 if row["on_duty"] == 1 else 1
        cur.execute(
            """
            UPDATE sahayak_roster
            SET on_duty = ?, last_active = ?
            WHERE id = ?;
            """,
            (new_duty, now_iso, sahayak_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="SAHAYAK_DUTY_TOGGLED",
            table_name="sahayak_roster",
            record_id=str(sahayak_id),
            after_state={"on_duty": new_duty},
        )

    return {"id": sahayak_id, "badge_number": row["badge_number"], "on_duty": bool(new_duty), "updated_at": now_iso}
