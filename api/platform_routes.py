"""RailTwin-X Platform Allocation Console & State Machine Endpoints (Module A3).

Provides platform state management (FREE, OCCUPIED, BLOCKED_MAINT, OUT_OF_SERVICE),
dynamic platform assignments, assignment locking, and safety interlock conflict checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import get_current_user, require_role
from data.audit import record_audit
from data.db import Database, get_db
from engine.ops import PlatformManager
from notifications.dispatcher import notify

router = APIRouter(prefix="/api/platform", tags=["Platform Allocation Console (A3)"])


class PlatformBlockRequest(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    platform: int = Field(..., ge=1, le=24, description="Platform number")
    state: str = Field("BLOCKED_MAINT", description="BLOCKED_MAINT, OUT_OF_SERVICE, FREE")
    reason: Optional[str] = Field("Track maintenance / point failure inspection")


class PlatformAssignRequest(BaseModel):
    station_code: str = Field("NDLS", description="Station code")
    train_no: str
    run_date: str = Field(..., description="YYYY-MM-DD")
    platform: int = Field(..., ge=1, le=24)
    assigned_arr: str = Field(..., description="HH:MM")
    assigned_dep: str = Field(..., description="HH:MM")
    is_locked: bool = Field(False, description="Lock assignment against AI re-optimization")


class PlatformLockRequest(BaseModel):
    is_locked: bool = True


@router.get("/states", response_model=List[Dict[str, Any]])
def get_platform_states(
    station_code: str = Query("NDLS", description="Station code"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Returns real-time occupancy and maintenance state for all station platforms."""
    stn = station_code.upper()
    with db.transaction() as cur:
        # Get platform count for station
        cur.execute("SELECT platforms FROM stations WHERE code = ?;", (stn,))
        stn_row = cur.fetchone()
        pf_count = stn_row["platforms"] if stn_row else 16

        cur.execute("SELECT * FROM platform_states WHERE station_code = ?;", (stn,))
        existing_states = {r["platform"]: dict(r) for r in cur.fetchall()}

    states = []
    for pf in range(1, pf_count + 1):
        if pf in existing_states:
            s = existing_states[pf]
            states.append({
                "station_code": stn,
                "platform": pf,
                "state": s["state"],
                "occupied_by_train": s["occupied_by_train"],
                "since": s["since"],
                "reason": s["reason"],
                "updated_by": s["updated_by"],
            })
        else:
            states.append({
                "station_code": stn,
                "platform": pf,
                "state": "FREE",
                "occupied_by_train": None,
                "since": datetime.now(timezone.utc).isoformat(),
                "reason": None,
                "updated_by": "system",
            })

    return states


@router.post("/block", response_model=Dict[str, Any])
def set_platform_block(
    req: PlatformBlockRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "engineer", "admin"])),
    db: Database = Depends(get_db),
):
    """Sets a platform state to BLOCKED_MAINT or OUT_OF_SERVICE or releases back to FREE."""
    stn = req.station_code.upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO platform_states (station_code, platform, state, occupied_by_train, since, reason, updated_by)
            VALUES (?, ?, ?, NULL, ?, ?, ?)
            ON CONFLICT(station_code, platform) DO UPDATE SET
                state = excluded.state,
                occupied_by_train = NULL,
                since = excluded.since,
                reason = excluded.reason,
                updated_by = excluded.updated_by;
            """,
            (stn, req.platform, req.state, now_iso, req.reason, current_user["id"]),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="PLATFORM_STATE_CHANGED",
            table_name="platform_states",
            record_id=f"{stn}-PF{req.platform}",
            after_state={"state": req.state, "reason": req.reason},
        )

    # Emit notification if blocked
    if req.state != "FREE":
        notify(
            event_type="PLATFORM_BLOCKED",
            target_roles=["station_master", "dy_sm", "section_controller", "engineer"],
            severity="warning",
            title=f"Platform {req.platform} Blocked at {stn}",
            message=f"Platform {req.platform} marked as {req.state}. Reason: {req.reason}",
            payload={"station_code": stn, "platform": req.platform, "state": req.state},
            station_code=stn,
            db=db,
        )

    return {
        "station_code": stn,
        "platform": req.platform,
        "state": req.state,
        "reason": req.reason,
        "updated_at": now_iso,
    }


@router.post("/assign", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def assign_platform(
    req: PlatformAssignRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Manually assigns or reallocates a train to a platform with conflict interlock validation."""
    stn = req.station_code.upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Conflict Check: verify platform is not blocked
    with db.transaction() as cur:
        cur.execute(
            "SELECT state, reason FROM platform_states WHERE station_code = ? AND platform = ?;",
            (stn, req.platform),
        )
        pf_row = cur.fetchone()
        if pf_row and pf_row["state"] in ("BLOCKED_MAINT", "OUT_OF_SERVICE"):
            raise HTTPException(
                status_code=400,
                detail=f"Platform {req.platform} is currently {pf_row['state']}: {pf_row['reason']}",
            )

        # 2. Conflict Check: verify no overlapping platform assignments
        cur.execute(
            """
            SELECT id, train_no, assigned_arr, assigned_dep
            FROM platform_assignments
            WHERE station_code = ? AND run_date = ? AND platform = ? AND status = 'SCHEDULED' AND train_no != ?;
            """,
            (stn, req.run_date, req.platform, req.train_no),
        )
        overlapping = cur.fetchall()

        arr_parts = [int(x) for x in req.assigned_arr.split(":")[:2]]
        dep_parts = [int(x) for x in req.assigned_dep.split(":")[:2]]
        req_start = arr_parts[0] * 60 + arr_parts[1]
        req_end = dep_parts[0] * 60 + dep_parts[1]

        for ov in overlapping:
            o_arr = [int(x) for x in ov["assigned_arr"].split(":")[:2]]
            o_dep = [int(x) for x in ov["assigned_dep"].split(":")[:2]]
            ov_start = o_arr[0] * 60 + o_arr[1]
            ov_end = o_dep[0] * 60 + o_dep[1]

            # Check overlap with 10 min headway buffer
            if max(req_start, ov_start) < min(req_end, ov_end) + 10:
                raise HTTPException(
                    status_code=409,
                    detail=f"Platform Conflict: Overlaps with Train #{ov['train_no']} ({ov['assigned_arr']}-{ov['assigned_dep']}) on PF {req.platform}.",
                )

        # 3. Upsert assignment
        cur.execute(
            """
            INSERT INTO platform_assignments (
                station_code, train_no, run_date, platform, assigned_arr,
                assigned_dep, is_locked, locked_by, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED', ?);
            """,
            (
                stn,
                req.train_no,
                req.run_date,
                req.platform,
                req.assigned_arr,
                req.assigned_dep,
                int(req.is_locked),
                current_user["id"] if req.is_locked else None,
                now_iso,
            ),
        )
        assign_id = cur.lastrowid

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="PLATFORM_ASSIGNED",
            table_name="platform_assignments",
            record_id=assign_id,
            after_state={"train_no": req.train_no, "platform": req.platform, "is_locked": req.is_locked},
        )

    return {
        "id": assign_id,
        "station_code": stn,
        "train_no": req.train_no,
        "platform": req.platform,
        "is_locked": req.is_locked,
        "status": "SCHEDULED",
    }


@router.post("/assignments/{assign_id}/lock", response_model=Dict[str, Any])
def toggle_assignment_lock(
    assign_id: int,
    req: PlatformLockRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Locks or unlocks a platform assignment to prevent AI re-optimizer from altering it."""
    with db.transaction() as cur:
        cur.execute("SELECT * FROM platform_assignments WHERE id = ?;", (assign_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Platform assignment not found.")

        cur.execute(
            """
            UPDATE platform_assignments
            SET is_locked = ?, locked_by = ?
            WHERE id = ?;
            """,
            (int(req.is_locked), current_user["id"] if req.is_locked else None, assign_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="PLATFORM_ASSIGNMENT_LOCK_TOGGLED",
            table_name="platform_assignments",
            record_id=assign_id,
            after_state={"is_locked": req.is_locked},
        )

    return {"id": assign_id, "is_locked": req.is_locked, "locked_by": current_user["id"] if req.is_locked else None}


class ReoptimizeRequest(BaseModel):
    station_code: Optional[str] = "CNB"
    target_date: Optional[str] = None


@router.post("/reoptimize", response_model=Dict[str, Any])
def reoptimize_station_platforms(
    payload: Optional[ReoptimizeRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Executes AI platform conflict resolution & Gantt re-optimization."""
    stn = (payload.station_code if payload and payload.station_code else "CNB").upper()
    target_date = payload.target_date if payload else None
    pm = PlatformManager(db)
    blocks, _ = pm.get_station_gantt(stn, target_date=target_date)
    reopt_blocks, diff = pm.reoptimize_platforms(stn, blocks)
    swaps_count = len(diff.swaps_performed) if isinstance(diff.swaps_performed, list) else int(diff.swaps_performed)
    return {
        "status": "success",
        "station_code": stn,
        "conflicts_before": diff.conflicts_before,
        "conflicts_after": diff.conflicts_after,
        "resolvedCount": diff.resolved_conflicts,
        "swapsCount": swaps_count,
        "swaps_performed": diff.swaps_performed,
        "execution_time_seconds": diff.execution_time_seconds,
        "message": f"Platform plan re-optimized: resolved {diff.resolved_conflicts} conflicts via {swaps_count} swaps.",
        "blocks": [b.to_dict() for b in reopt_blocks],
    }
