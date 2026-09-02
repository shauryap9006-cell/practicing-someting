"""RailTwin-X Maintenance & Infrastructure Engineering API (Phase 5 - Modules G1, G2, G3).

Provides:
- G1: Rolling Stock Rake Health & Brake Power Certificate (BPC) Registry
- G2: Station Fixed Asset Register & Defect Work Orders
- G3: Cleanliness & Bio-Toilet Feedback Logs
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

router = APIRouter(tags=["Maintenance & Infrastructure (Phase 5)"])


# ----------------------------------------------------
# G1. ROLLING STOCK RAKE HEALTH & BPC REGISTER
# ----------------------------------------------------
class RakeBpcCreate(BaseModel):
    rake_id: str
    train_no: Optional[str] = None
    bpc_number: str
    bpc_issue_date: str
    bpc_valid_until: str
    bpc_type: str = Field("PREMIUM", description="PREMIUM, CC_INTENSIVE, END_TO_END, SPECIAL")
    brake_power_percent: float = Field(100.0, ge=0.0, le=100.0)
    air_brake_pressure_kg: float = Field(5.0, ge=0.0)
    coach_count: int = Field(22, ge=1)
    notes: Optional[str] = None


@router.post("/rakes", response_model=Dict[str, Any])
def register_rake_bpc(
    req: RakeBpcCreate,
    current_user: Dict[str, Any] = Depends(require_role(["engineer", "station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Registers a rolling stock rake and its official Brake Power Certificate (BPC)."""
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO rakes (
                rake_id, train_no, bpc_number, bpc_issue_date, bpc_valid_until,
                bpc_type, brake_power_percent, air_brake_pressure_kg,
                coach_count, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            ON CONFLICT(rake_id) DO UPDATE SET
                train_no = excluded.train_no,
                bpc_number = excluded.bpc_number,
                bpc_valid_until = excluded.bpc_valid_until,
                brake_power_percent = excluded.brake_power_percent,
                status = 'ACTIVE';
            """,
            (
                req.rake_id,
                req.train_no,
                req.bpc_number,
                req.bpc_issue_date,
                req.bpc_valid_until,
                req.bpc_type.upper(),
                req.brake_power_percent,
                req.air_brake_pressure_kg,
                req.coach_count,
                req.notes,
            ),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="RAKE_BPC_REGISTERED",
            table_name="rakes",
            record_id=req.rake_id,
            after_state={"bpc": req.bpc_number, "valid_until": req.bpc_valid_until, "brake_power": req.brake_power_percent},
        )

    return {"rake_id": req.rake_id, "bpc_number": req.bpc_number, "status": "ACTIVE"}


@router.get("/rakes", response_model=List[Dict[str, Any]])
def list_rakes(
    train_no: Optional[str] = Query(None, description="Filter by train number"),
    overdue_only: bool = Query(False, description="Filter for overdue BPCs only"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists rolling stock rakes and BPC certification statuses."""
    with db.transaction() as cur:
        # Seed sample rakes if empty
        cur.execute("SELECT COUNT(*) as count FROM rakes;")
        c = cur.fetchone()["count"]
        if c == 0:
            sample_rakes = [
                ("RAKE-12004-A", "12004", "BPC-NR-2026-891", "2026-08-25", "2026-08-31", "PREMIUM", 100.0, 5.0, 18, "ACTIVE"),
                ("RAKE-12424-B", "12424", "BPC-NR-2026-892", "2026-08-24", "2026-08-30", "PREMIUM", 98.5, 5.0, 22, "ACTIVE"),
                ("RAKE-FRT-901", "BOXN-901", "BPC-CC-2026-104", "2026-08-01", "2026-08-27", "CC_INTENSIVE", 85.0, 4.8, 58, "OVERDUE"),
            ]
            for rk in sample_rakes:
                cur.execute(
                    """
                    INSERT INTO rakes (
                        rake_id, train_no, bpc_number, bpc_issue_date, bpc_valid_until,
                        bpc_type, brake_power_percent, air_brake_pressure_kg,
                        coach_count, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    rk,
                )

        query = "SELECT * FROM rakes WHERE 1=1"
        params: List[Any] = []
        if train_no:
            query += " AND train_no = ?"
            params.append(train_no)
        if overdue_only:
            query += " AND status = 'OVERDUE'"
        query += " ORDER BY id DESC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


# ----------------------------------------------------
# G2. STATION FIXED ASSET REGISTER & WORK ORDERS
# ----------------------------------------------------
class StationAssetCreate(BaseModel):
    asset_tag: str = Field(..., description="e.g. SIG-NDLS-01 or TN-NDLS-22")
    asset_type: str = Field("TURNOUT", description="TURNOUT, SIGNAL, OHE_SECTION, TRACK_CIRCUIT, POINT_MACHINE, CCTV, PA_SPEAKER")
    station_code: str = "NDLS"
    platform_or_track: str = "Platform 1"
    last_serviced_date: str
    next_service_due: str
    notes: Optional[str] = None


@router.post("/assets", response_model=Dict[str, Any])
def register_station_asset(
    req: StationAssetCreate,
    current_user: Dict[str, Any] = Depends(require_role(["engineer", "station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Registers or updates a fixed station infrastructure asset."""
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO station_assets (
                asset_tag, asset_type, station_code, platform_or_track,
                status, last_serviced_date, next_service_due, notes
            )
            VALUES (?, ?, ?, ?, 'OPERATIONAL', ?, ?, ?)
            ON CONFLICT(asset_tag) DO UPDATE SET
                platform_or_track = excluded.platform_or_track,
                last_serviced_date = excluded.last_serviced_date,
                next_service_due = excluded.next_service_due,
                status = 'OPERATIONAL';
            """,
            (
                req.asset_tag.upper(),
                req.asset_type.upper(),
                req.station_code.upper(),
                req.platform_or_track,
                req.last_serviced_date,
                req.next_service_due,
                req.notes,
            ),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="STATION_ASSET_REGISTERED",
            table_name="station_assets",
            record_id=req.asset_tag,
            after_state={"tag": req.asset_tag, "type": req.asset_type},
        )

    return {"asset_tag": req.asset_tag, "status": "OPERATIONAL"}


@router.get("/assets", response_model=List[Dict[str, Any]])
def list_station_assets(
    station_code: Optional[str] = Query(None, description="Station filter"),
    asset_type: Optional[str] = Query(None, description="Asset type filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists station fixed assets."""
    with db.transaction() as cur:
        # Seed default sample assets if empty
        cur.execute("SELECT COUNT(*) as count FROM station_assets;")
        c = cur.fetchone()["count"]
        if c == 0:
            sample_assets = [
                ("SIG-NDLS-01", "SIGNAL", "NDLS", "Main Line North", "OPERATIONAL", "2026-08-01", "2026-09-01"),
                ("TN-NDLS-14A", "TURNOUT", "NDLS", "Cross-over 14A/B", "OPERATIONAL", "2026-07-15", "2026-08-30"),
                ("OHE-NDLS-SEC2", "OHE_SECTION", "NDLS", "Yard Grid North", "OPERATIONAL", "2026-08-10", "2026-09-10"),
                ("PM-NDLS-08", "POINT_MACHINE", "NDLS", "PF 1 Throat", "DEFECTIVE", "2026-06-01", "2026-08-15"),
                ("TC-NDLS-102", "TRACK_CIRCUIT", "NDLS", "Block Section Inbound", "OPERATIONAL", "2026-08-20", "2026-09-20"),
            ]
            for a in sample_assets:
                cur.execute(
                    """
                    INSERT INTO station_assets (
                        asset_tag, asset_type, station_code, platform_or_track,
                        status, last_serviced_date, next_service_due
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    a,
                )

        query = "SELECT * FROM station_assets WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        if asset_type:
            query += " AND asset_type = ?"
            params.append(asset_type.upper())
        if status:
            query += " AND status = ?"
            params.append(status.upper())
        query += " ORDER BY asset_type ASC, asset_tag ASC;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


class WorkOrderCreate(BaseModel):
    asset_tag: str
    station_code: str = "NDLS"
    issue_description: str
    priority: str = Field("HIGH", description="LOW, MEDIUM, HIGH, URGENT")
    assigned_to: Optional[str] = "SE (Signals) Team"


@router.post("/work-orders", response_model=Dict[str, Any])
def create_work_order(
    req: WorkOrderCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Logs a maintenance work order against a defective asset."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO work_orders (
                asset_tag, station_code, issue_description, priority,
                status, reported_by, assigned_to, created_at
            )
            VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?);
            """,
            (
                req.asset_tag.upper(),
                req.station_code.upper(),
                req.issue_description,
                req.priority.upper(),
                current_user["id"],
                req.assigned_to,
                now_iso,
            ),
        )
        wo_id = cur.lastrowid

        # Update asset state to DEFECTIVE
        cur.execute(
            "UPDATE station_assets SET status = 'DEFECTIVE' WHERE asset_tag = ?;",
            (req.asset_tag.upper(),),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="WORK_ORDER_CREATED",
            table_name="work_orders",
            record_id=str(wo_id),
            after_state={"asset": req.asset_tag, "priority": req.priority, "desc": req.issue_description},
        )

    # Notify engineering staff
    notify(
        event_type="WORK_ORDER_LOGGED",
        target_roles=["engineer", "station_master", "dy_sm", "section_controller"],
        severity="warn" if req.priority.upper() != "URGENT" else "critical",
        title=f"🔧 DEFECT LOGGED: {req.asset_tag} ({req.priority})",
        message=f"Work Order #{wo_id} created for {req.asset_tag} at {req.station_code}: {req.issue_description}.",
        payload={"wo_id": wo_id, "asset_tag": req.asset_tag, "priority": req.priority},
        db=db,
    )

    return {"id": wo_id, "asset_tag": req.asset_tag, "status": "OPEN", "priority": req.priority, "created_at": now_iso}


@router.get("/work-orders", response_model=List[Dict[str, Any]])
def list_work_orders(
    station_code: Optional[str] = Query(None, description="Station filter"),
    status: Optional[str] = Query(None, description="OPEN, IN_PROGRESS, RESOLVED"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists maintenance work orders."""
    with db.transaction() as cur:
        query = "SELECT * FROM work_orders WHERE 1=1"
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


class ResolveWorkOrderRequest(BaseModel):
    resolution_notes: str


@router.put("/work-orders/{wo_id}/resolve", response_model=Dict[str, Any])
def resolve_work_order(
    wo_id: int,
    req: ResolveWorkOrderRequest,
    current_user: Dict[str, Any] = Depends(require_role(["engineer", "station_master", "admin"])),
    db: Database = Depends(get_db),
):
    """Marks a work order as RESOLVED and restores asset to OPERATIONAL status."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM work_orders WHERE id = ?;", (wo_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Work order not found.")

        cur.execute(
            """
            UPDATE work_orders
            SET status = 'RESOLVED', resolved_at = ?, resolution_notes = ?
            WHERE id = ?;
            """,
            (now_iso, req.resolution_notes, wo_id),
        )

        # Restore asset to OPERATIONAL
        cur.execute(
            "UPDATE station_assets SET status = 'OPERATIONAL', last_serviced_date = ? WHERE asset_tag = ?;",
            (now_iso.slice if hasattr(now_iso, 'slice') else now_iso[:10], row["asset_tag"]),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="WORK_ORDER_RESOLVED",
            table_name="work_orders",
            record_id=str(wo_id),
            before_state=dict(row),
            after_state={"status": "RESOLVED", "notes": req.resolution_notes},
        )

    return {"id": wo_id, "status": "RESOLVED", "resolved_at": now_iso}


# ----------------------------------------------------
# G3. CLEANLINESS & BIO-TOILET FEEDBACK
# ----------------------------------------------------
class CleaningLogCreate(BaseModel):
    station_code: str = "NDLS"
    area_type: str = Field("PLATFORM", description="PLATFORM, WAITING_HALL, TOILET, CONCOURSE, FOOT_OVER_BRIDGE")
    platform_number: Optional[int] = 1
    score_1_to_5: int = Field(5, ge=1, le=5)
    contractor_name: Optional[str] = "Swachh Rail Agency"
    notes: Optional[str] = None


@router.post("/cleaning-logs", response_model=Dict[str, Any])
def record_cleaning_log(
    req: CleaningLogCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Records a cleanliness inspection score for a station zone."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO cleaning_logs (
                station_code, area_type, platform_number, cleaned_at,
                inspected_by, score_1_to_5, contractor_name, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                req.station_code.upper(),
                req.area_type.upper(),
                req.platform_number,
                now_iso,
                current_user["id"],
                req.score_1_to_5,
                req.contractor_name or "Swachh Rail Agency",
                req.notes,
            ),
        )
        log_id = cur.lastrowid

    return {"id": log_id, "score": req.score_1_to_5, "cleaned_at": now_iso}


@router.get("/cleaning-logs", response_model=List[Dict[str, Any]])
@router.get("/feedback", response_model=List[Dict[str, Any]])
def list_cleaning_logs(
    station_code: Optional[str] = Query(None, description="Station filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Lists cleanliness audit logs."""
    with db.transaction() as cur:
        # Seed sample cleaning logs if empty
        cur.execute("SELECT COUNT(*) as count FROM cleaning_logs;")
        c = cur.fetchone()["count"]
        if c == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            sample_logs = [
                ("NDLS", "PLATFORM", 1, now_iso, "usr-sm-ndls-01", 5, "Swachh Rail Agency", "Thoroughly washed with scrubber machine"),
                ("NDLS", "TOILET", 2, now_iso, "usr-sm-ndls-01", 4, "Swachh Rail Agency", "Disinfected and soap refilled"),
                ("NDLS", "WAITING_HALL", 1, now_iso, "usr-sm-ndls-01", 5, "Swachh Rail Agency", "Floor buffed and dustbins emptied"),
            ]
            for cl in sample_logs:
                cur.execute(
                    """
                    INSERT INTO cleaning_logs (
                        station_code, area_type, platform_number, cleaned_at,
                        inspected_by, score_1_to_5, contractor_name, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    cl,
                )

        query = "SELECT * FROM cleaning_logs WHERE 1=1"
        params: List[Any] = []
        if station_code:
            query += " AND station_code = ?"
            params.append(station_code.upper())
        query += " ORDER BY id DESC LIMIT 50;"
        cur.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
    return rows
