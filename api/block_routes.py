"""RailTwin-X Block Section & Line Status Board Endpoints (Module A5).

Provides corridor block section occupancy management, Line Clear grant workflows,
and Speed Restriction (TSR) caution overlays.
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

router = APIRouter(prefix="/api/blocks", tags=["Block Sections & Line Status (A5)"])


class BlockStateUpdate(BaseModel):
    state: str = Field(..., description="CLEAR, OCCUPIED, BLOCKED, CAUTION")
    occupied_by_train: Optional[str] = None
    notes: Optional[str] = None


class LineClearGrantRequest(BaseModel):
    train_no: str
    notes: Optional[str] = "Line Clear Granted"


@router.get("/status", response_model=List[Dict[str, Any]])
def get_block_statuses(
    station_code: Optional[str] = Query(None, description="Station code filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Returns corridor block sections with active state, train occupancy, and caution restrictions."""
    with db.transaction() as cur:
        # Fetch sections (distance_km, max_speed_kmph, single_line)
        cur.execute("SELECT from_code, to_code, distance_km, max_speed_kmph, single_line FROM sections;")
        sec_rows = cur.fetchall()

        # Fetch block statuses
        cur.execute("SELECT * FROM block_status;")
        bs_rows = {r["block_id"]: dict(r) for r in cur.fetchall()}

        # Fetch active speed restrictions if table exists
        srs = []
        try:
            cur.execute(
                """
                SELECT from_code, to_code, speed_limit_kmph, cause
                FROM speed_restrictions
                WHERE status = 'ACTIVE';
                """
            )
            srs = cur.fetchall()
        except Exception:
            pass

    sr_map = {(sr["from_code"], sr["to_code"]): sr for sr in srs}

    blocks = []
    for sec in sec_rows:
        f_code = sec["from_code"]
        t_code = sec["to_code"]
        b_id = f"BLK-{f_code}-{t_code}"

        if station_code and station_code.upper() not in (f_code, t_code):
            continue

        bs = bs_rows.get(b_id, {})
        has_sr = (f_code, t_code) in sr_map or (t_code, f_code) in sr_map
        active_sr = sr_map.get((f_code, t_code)) or sr_map.get((t_code, f_code))

        default_state = "CAUTION" if has_sr else "CLEAR"
        state = bs.get("state", default_state)
        tracks_count = 1 if sec["single_line"] else 2

        blocks.append({
            "block_id": b_id,
            "from_code": f_code,
            "to_code": t_code,
            "length_km": sec["distance_km"],
            "max_speed_kmph": sec["max_speed_kmph"],
            "tracks": tracks_count,
            "state": state,
            "occupied_by_train": bs.get("occupied_by_train"),
            "line_clear_granted_to": bs.get("line_clear_granted_to"),
            "granted_by": bs.get("granted_by"),
            "since": bs.get("since", datetime.now(timezone.utc).isoformat()),
            "notes": bs.get("notes"),
            "caution_speed_limit": active_sr["speed_limit_kmph"] if active_sr else None,
            "caution_cause": active_sr["cause"] if active_sr else None,
        })

    return blocks


@router.post("/{block_id}/state", response_model=Dict[str, Any])
def update_block_state(
    block_id: str,
    req: BlockStateUpdate,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Updates block section state (CLEAR, OCCUPIED, BLOCKED, CAUTION)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    parts = block_id.replace("BLK-", "").split("-")
    f_code = parts[0] if len(parts) > 0 else "NDLS"
    t_code = parts[1] if len(parts) > 1 else "GZB"

    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO block_status (block_id, from_code, to_code, state, occupied_by_train, since, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(block_id) DO UPDATE SET
                state = excluded.state,
                occupied_by_train = excluded.occupied_by_train,
                since = excluded.since,
                notes = excluded.notes;
            """,
            (block_id, f_code, t_code, req.state.upper(), req.occupied_by_train, now_iso, req.notes),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="BLOCK_STATE_UPDATED",
            table_name="block_status",
            record_id=block_id,
            after_state={"state": req.state.upper(), "occupied_by_train": req.occupied_by_train},
        )

    return {"block_id": block_id, "state": req.state.upper(), "updated_at": now_iso}


@router.post("/{block_id}/line-clear", response_model=Dict[str, Any])
def grant_line_clear(
    block_id: str,
    req: LineClearGrantRequest,
    current_user: Dict[str, Any] = Depends(require_role(["station_master", "section_controller", "admin"])),
    db: Database = Depends(get_db),
):
    """Grants Line Clear authority for a train into the block section."""
    now_iso = datetime.now(timezone.utc).isoformat()
    parts = block_id.replace("BLK-", "").split("-")
    f_code = parts[0] if len(parts) > 0 else "NDLS"
    t_code = parts[1] if len(parts) > 1 else "GZB"

    with db.transaction() as cur:
        cur.execute("SELECT state FROM block_status WHERE block_id = ?;", (block_id,))
        b_row = cur.fetchone()
        if b_row and b_row["state"] == "BLOCKED":
            raise HTTPException(status_code=400, detail=f"Cannot grant Line Clear: Block {block_id} is BLOCKED.")

        cur.execute(
            """
            INSERT INTO block_status (
                block_id, from_code, to_code, state, line_clear_granted_to,
                granted_by, since, notes
            )
            VALUES (?, ?, ?, 'OCCUPIED', ?, ?, ?, ?)
            ON CONFLICT(block_id) DO UPDATE SET
                state = 'OCCUPIED',
                line_clear_granted_to = excluded.line_clear_granted_to,
                granted_by = excluded.granted_by,
                since = excluded.since,
                notes = excluded.notes;
            """,
            (block_id, f_code, t_code, req.train_no, current_user["id"], now_iso, req.notes),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=current_user["id"],
            actor_role=current_user["role_id"],
            action="LINE_CLEAR_GRANTED",
            table_name="block_status",
            record_id=block_id,
            after_state={"train_no": req.train_no, "granted_by": current_user["id"]},
        )

    # Emit notification
    notify(
        event_type="LINE_CLEAR_GRANTED",
        target_roles=["station_master", "dy_sm", "section_controller", "viewer"],
        severity="info",
        title=f"Line Clear: Block {block_id} -> Train #{req.train_no}",
        message=f"Line Clear granted for Train #{req.train_no} across block {block_id} by {current_user['full_name']}.",
        payload={"block_id": block_id, "train_no": req.train_no},
        db=db,
    )

    return {
        "block_id": block_id,
        "train_no": req.train_no,
        "status": "LINE_CLEAR_GRANTED",
        "granted_by": current_user["id"],
        "granted_at": now_iso,
    }
