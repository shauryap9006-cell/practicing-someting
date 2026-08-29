"""RailTwin-X Audit Trail API Endpoints (Module I3).

Provides endpoints to query the append-only audit trail and execute real-time SHA-256
cryptographic chain integrity verification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import require_role
from data.audit import verify_audit_chain_integrity
from data.db import Database, get_db

router = APIRouter(prefix="/api/audit", tags=["Audit & Provenance"])


class AuditLogItem(BaseModel):
    id: int
    ts: str
    actor_id: str
    actor_role: str
    action: str
    table_name: str
    record_id: str
    before_state: Optional[str]
    after_state: Optional[str]
    row_hash: str
    prev_hash: str


class AuditQueryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    logs: List[AuditLogItem]


class IntegrityVerifyResponse(BaseModel):
    is_valid: bool
    total_records_checked: int
    error_detail: Optional[str] = None


@router.get("/logs", response_model=AuditQueryResponse)
def get_audit_logs(
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action code"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master", "dy_sm"])),
    db: Database = Depends(get_db),
):
    """Retrieves paginated audit log entries with optional filtering."""
    query = "SELECT id, ts, actor_id, actor_role, action, table_name, record_id, before_state, after_state, row_hash, prev_hash FROM audit_log WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
    params: List[Any] = []

    if table_name:
        query += " AND table_name = ?"
        count_query += " AND table_name = ?"
        params.append(table_name)
    if actor_id:
        query += " AND actor_id = ?"
        count_query += " AND actor_id = ?"
        params.append(actor_id)
    if action:
        query += " AND action = ?"
        count_query += " AND action = ?"
        params.append(action)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
    query_params = params + [limit, offset]

    with db.transaction() as cur:
        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        cur.execute(query, query_params)
        rows = cur.fetchall()

    logs = [
        AuditLogItem(
            id=r["id"],
            ts=r["ts"],
            actor_id=r["actor_id"],
            actor_role=r["actor_role"],
            action=r["action"],
            table_name=r["table_name"],
            record_id=r["record_id"],
            before_state=r["before_state"],
            after_state=r["after_state"],
            row_hash=r["row_hash"],
            prev_hash=r["prev_hash"],
        )
        for r in rows
    ]

    return AuditQueryResponse(total=total, limit=limit, offset=offset, logs=logs)


@router.get("/verify-integrity", response_model=IntegrityVerifyResponse)
def verify_audit_trail_integrity(
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master"])),
    db: Database = Depends(get_db),
):
    """Executes a full-chain cryptographic audit verification confirming no records have been altered."""
    is_valid, count, err = verify_audit_chain_integrity(db=db)
    return IntegrityVerifyResponse(
        is_valid=is_valid,
        total_records_checked=count,
        error_detail=err,
    )
