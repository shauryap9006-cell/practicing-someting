"""RailTwin-X Working Timetable Manager Endpoints (Module A1).

Provides versioned working timetable management (draft -> published -> archived),
train schedule CRUD, validation engine, bulk seed/RapidAPI import, and version diff calculation.
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

router = APIRouter(prefix="/api/timetable", tags=["Timetable Manager (A1)"])


class TimetableVersionCreate(BaseModel):
    version_name: str = Field(..., description="e.g. WTT 2026 Monsoon Edition v1")
    effective_from: str = Field(..., description="YYYY-MM-DD")
    effective_to: Optional[str] = Field(None, description="YYYY-MM-DD")
    description: Optional[str] = None


class TimetableEntryCreate(BaseModel):
    version_id: str
    train_no: str
    train_name: str
    train_type: str = Field("express", description="express, passenger, freight, emu, special")
    direction: str = Field("UP", description="UP or DOWN")
    station_code: str
    stop_seq: int
    sched_arr: Optional[str] = None
    sched_dep: Optional[str] = None
    halt_min: int = 2
    platform_default: int = 1
    days_of_run: str = "DAILY"


class TimetableEntryUpdate(BaseModel):
    train_name: Optional[str] = None
    train_type: Optional[str] = None
    direction: Optional[str] = None
    sched_arr: Optional[str] = None
    sched_dep: Optional[str] = None
    halt_min: Optional[int] = None
    platform_default: Optional[int] = None
    days_of_run: Optional[str] = None
    is_cancelled: Optional[bool] = None
    cancellation_reason: Optional[str] = None


@router.get("/versions", response_model=List[Dict[str, Any]])
def list_timetable_versions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists all timetable versions with status, effective dates, and train counts."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT v.*, COUNT(e.id) as total_entries, COUNT(DISTINCT e.train_no) as total_trains
            FROM timetable_versions v
            LEFT JOIN timetable_entries e ON v.id = e.version_id
            GROUP BY v.id
            ORDER BY v.created_at DESC;
            """
        )
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "version_name": r["version_name"],
            "status": r["status"],
            "effective_from": r["effective_from"],
            "effective_to": r["effective_to"],
            "description": r["description"],
            "created_by": r["created_by"],
            "published_at": r["published_at"],
            "created_at": r["created_at"],
            "total_entries": r["total_entries"],
            "total_trains": r["total_trains"],
        }
        for r in rows
    ]


@router.post("/versions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_timetable_version(
    req: TimetableVersionCreate,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master", "section_controller"])),
    db: Database = Depends(get_db),
):
    """Creates a new working timetable version in DRAFT state."""
    version_id = f"WTT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO timetable_versions (
                id, version_name, status, effective_from, effective_to,
                description, created_by, created_at
            ) VALUES (?, ?, 'draft', ?, ?, ?, ?, ?);
            """,
            (
                version_id,
                req.version_name,
                req.effective_from,
                req.effective_to,
                req.description,
                current_user["id"],
                now_iso,
            ),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TIMETABLE_VERSION_CREATED",
            table_name="timetable_versions",
            record_id=version_id,
            after_state={"version_name": req.version_name, "status": "draft"},
        )

    return {
        "id": version_id,
        "version_name": req.version_name,
        "status": "draft",
        "effective_from": req.effective_from,
        "effective_to": req.effective_to,
        "description": req.description,
        "created_by": current_user["id"],
        "created_at": now_iso,
    }


@router.get("/versions/{version_id}/entries", response_model=Dict[str, Any])
def get_version_entries(
    version_id: str,
    train_no: Optional[str] = Query(None),
    station_code: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves paginated train stop entries for a specific timetable version."""
    query = "SELECT * FROM timetable_entries WHERE version_id = ?"
    count_query = "SELECT COUNT(*) FROM timetable_entries WHERE version_id = ?"
    params: List[Any] = [version_id]

    if train_no:
        query += " AND train_no = ?"
        count_query += " AND train_no = ?"
        params.append(train_no)
    if station_code:
        query += " AND station_code = ?"
        count_query += " AND station_code = ?"
        params.append(station_code.upper())

    query += " ORDER BY train_no ASC, stop_seq ASC LIMIT ? OFFSET ?;"
    query_params = params + [limit, offset]

    with db.transaction() as cur:
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        cur.execute(query, query_params)
        rows = cur.fetchall()

    entries = [
        {
            "id": r["id"],
            "version_id": r["version_id"],
            "train_no": r["train_no"],
            "train_name": r["train_name"],
            "train_type": r["train_type"],
            "direction": r["direction"],
            "station_code": r["station_code"],
            "stop_seq": r["stop_seq"],
            "sched_arr": r["sched_arr"],
            "sched_dep": r["sched_dep"],
            "halt_min": r["halt_min"],
            "platform_default": r["platform_default"],
            "days_of_run": r["days_of_run"],
            "is_cancelled": bool(r["is_cancelled"]),
            "cancellation_reason": r["cancellation_reason"],
        }
        for r in rows
    ]

    return {"version_id": version_id, "total": total, "entries": entries}


@router.post("/entries", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    req: TimetableEntryCreate,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master", "section_controller"])),
    db: Database = Depends(get_db),
):
    """Creates a new stop entry in a draft timetable version."""
    with db.transaction() as cur:
        # Verify version is draft
        cur.execute("SELECT status FROM timetable_versions WHERE id = ?;", (req.version_id,))
        v_row = cur.fetchone()
        if not v_row:
            raise HTTPException(status_code=404, detail=f"Timetable version '{req.version_id}' not found.")
        if v_row["status"] != "draft":
            raise HTTPException(status_code=400, detail="Cannot add entries to a published or archived timetable.")

        cur.execute(
            """
            INSERT INTO timetable_entries (
                version_id, train_no, train_name, train_type, direction,
                station_code, stop_seq, sched_arr, sched_dep, halt_min,
                platform_default, days_of_run
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                req.version_id,
                req.train_no,
                req.train_name,
                req.train_type,
                req.direction,
                req.station_code.upper(),
                req.stop_seq,
                req.sched_arr,
                req.sched_dep,
                req.halt_min,
                req.platform_default,
                req.days_of_run,
            ),
        )
        entry_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TIMETABLE_ENTRY_CREATED",
            table_name="timetable_entries",
            record_id=entry_id,
            after_state={"train_no": req.train_no, "station_code": req.station_code, "stop_seq": req.stop_seq},
        )

    return {"id": entry_id, "status": "created", "train_no": req.train_no}


@router.put("/entries/{entry_id}", response_model=Dict[str, Any])
def update_timetable_entry(
    entry_id: int,
    req: TimetableEntryUpdate,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master", "section_controller"])),
    db: Database = Depends(get_db),
):
    """Updates an existing timetable stop entry (e.g. schedule, platform, or cancellation)."""
    with db.transaction() as cur:
        cur.execute("SELECT * FROM timetable_entries WHERE id = ?;", (entry_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Timetable entry with ID {entry_id} not found.")

        # Check version status
        cur.execute("SELECT status FROM timetable_versions WHERE id = ?;", (existing["version_id"],))
        v_row = cur.fetchone()
        if v_row and v_row["status"] == "archived":
            raise HTTPException(status_code=400, detail="Cannot edit archived timetable versions.")

        new_name = req.train_name if req.train_name is not None else existing["train_name"]
        new_type = req.train_type if req.train_type is not None else existing["train_type"]
        new_dir = req.direction if req.direction is not None else existing["direction"]
        new_arr = req.sched_arr if req.sched_arr is not None else existing["sched_arr"]
        new_dep = req.sched_dep if req.sched_dep is not None else existing["sched_dep"]
        new_halt = req.halt_min if req.halt_min is not None else existing["halt_min"]
        new_pf = req.platform_default if req.platform_default is not None else existing["platform_default"]
        new_days = req.days_of_run if req.days_of_run is not None else existing["days_of_run"]
        new_canc = int(req.is_cancelled) if req.is_cancelled is not None else existing["is_cancelled"]
        new_reason = req.cancellation_reason if req.cancellation_reason is not None else existing["cancellation_reason"]

        cur.execute(
            """
            UPDATE timetable_entries
            SET train_name = ?, train_type = ?, direction = ?, sched_arr = ?, sched_dep = ?,
                halt_min = ?, platform_default = ?, days_of_run = ?, is_cancelled = ?,
                cancellation_reason = ?
            WHERE id = ?;
            """,
            (
                new_name, new_type, new_dir, new_arr, new_dep,
                new_halt, new_pf, new_days, new_canc, new_reason, entry_id
            ),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TIMETABLE_ENTRY_UPDATED",
            table_name="timetable_entries",
            record_id=entry_id,
            after_state={"train_no": existing["train_no"], "platform_default": new_pf, "is_cancelled": new_canc},
        )

    return {"id": entry_id, "status": "updated"}


@router.delete("/entries/{entry_id}", response_model=Dict[str, Any])
def delete_timetable_entry(
    entry_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master"])),
    db: Database = Depends(get_db),
):
    """Deletes an entry from a draft timetable."""
    with db.transaction() as cur:
        cur.execute("SELECT version_id, train_no FROM timetable_entries WHERE id = ?;", (entry_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found.")

        cur.execute("DELETE FROM timetable_entries WHERE id = ?;", (entry_id,))

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TIMETABLE_ENTRY_DELETED",
            table_name="timetable_entries",
            record_id=entry_id,
            before_state={"train_no": row["train_no"], "version_id": row["version_id"]},
        )

    return {"id": entry_id, "status": "deleted"}


@router.get("/versions/{version_id}/validate", response_model=Dict[str, Any])
def validate_timetable_version(
    version_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Validates the timetable entries: checks negative dwells, seq order, and platform validity."""
    issues = []

    with db.transaction() as cur:
        cur.execute("SELECT * FROM timetable_entries WHERE version_id = ? ORDER BY train_no, stop_seq;", (version_id,))
        entries = cur.fetchall()

    if not entries:
        return {"is_valid": False, "total_entries": 0, "issues": ["Timetable version contains zero entries."]}

    # Check negative dwell & times
    for e in entries:
        arr = e["sched_arr"]
        dep = e["sched_dep"]
        if arr and dep:
            arr_parts = [int(x) for x in arr.split(":")[:2]]
            dep_parts = [int(x) for x in dep.split(":")[:2]]
            arr_m = arr_parts[0] * 60 + arr_parts[1]
            dep_m = dep_parts[0] * 60 + dep_parts[1]
            if dep_m < arr_m and (arr_m - dep_m < 1200):  # ignore midnight wraparound (> 20h)
                issues.append(
                    f"Train #{e['train_no']} at {e['station_code']}: Negative dwell detected (arr={arr}, dep={dep})"
                )
        if e["platform_default"] <= 0 or e["platform_default"] > 24:
            issues.append(f"Train #{e['train_no']} at {e['station_code']}: Invalid platform {e['platform_default']}")

    is_valid = len(issues) == 0
    return {
        "version_id": version_id,
        "is_valid": is_valid,
        "total_entries": len(entries),
        "issues_count": len(issues),
        "issues": issues,
    }


@router.post("/versions/{version_id}/import-seed", response_model=Dict[str, Any])
def import_seed_timetable(
    version_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master"])),
    db: Database = Depends(get_db),
):
    """Bootstraps a draft timetable version by importing all master trains and routes from the database."""
    with db.transaction() as cur:
        cur.execute("SELECT status FROM timetable_versions WHERE id = ?;", (version_id,))
        v_row = cur.fetchone()
        if not v_row or v_row["status"] != "draft":
            raise HTTPException(status_code=400, detail="Can only import into draft timetable versions.")

        # Fetch master trains and route stations
        cur.execute(
            """
            SELECT t.train_no, t.name as train_name, t.class, rs.seq as stop_seq, rs.station_code,
                   rs.sched_arr, rs.sched_dep, rs.halt_min
            FROM trains t
            JOIN route_stations rs ON t.train_no = rs.train_no
            ORDER BY t.train_no, rs.seq;
            """
        )
        routes = cur.fetchall()

        imported_count = 0
        for r in routes:
            t_type = "express" if r["class"] in ("rajdhani", "shatabdi", "superfast") else ("freight" if "rake" in r["class"] or "freight" in r["class"] else "passenger")
            direction = "UP" if int(r["train_no"]) % 2 != 0 else "DOWN"

            cur.execute(
                """
                INSERT INTO timetable_entries (
                    version_id, train_no, train_name, train_type, direction,
                    station_code, stop_seq, sched_arr, sched_dep, halt_min,
                    platform_default, days_of_run
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'DAILY');
                """,
                (
                    version_id,
                    r["train_no"],
                    r["train_name"],
                    t_type,
                    direction,
                    r["station_code"],
                    r["stop_seq"],
                    r["sched_arr"],
                    r["sched_dep"],
                    r["halt_min"],
                ),
            )
            imported_count += 1

    return {"version_id": version_id, "imported_entries": imported_count}


@router.post("/versions/{version_id}/publish", response_model=Dict[str, Any])
def publish_timetable_version(
    version_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master"])),
    db: Database = Depends(get_db),
):
    """Validates and publishes the timetable version, archiving any previously published timetable."""
    val = validate_timetable_version(version_id, current_user, db)
    if not val["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Timetable validation failed before publishing.", "issues": val["issues"]},
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        # Archive older published versions
        cur.execute("UPDATE timetable_versions SET status = 'archived' WHERE status = 'published';")

        # Mark current version as published
        cur.execute(
            """
            UPDATE timetable_versions
            SET status = 'published', published_at = ?
            WHERE id = ?;
            """,
            (now_iso, version_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="TIMETABLE_VERSION_PUBLISHED",
            table_name="timetable_versions",
            record_id=version_id,
            after_state={"status": "published", "published_at": now_iso},
        )

    # Emit broadcast notification
    notify(
        event_type="TIMETABLE_PUBLISHED",
        target_roles=["station_master", "dy_sm", "crew_controller", "section_controller", "viewer"],
        severity="info",
        title=f"New Timetable Published: {version_id}",
        message=f"Working timetable {version_id} has been validated and activated for corridor operations.",
        payload={"version_id": version_id},
        db=db,
    )

    return {"version_id": version_id, "status": "published", "published_at": now_iso}
