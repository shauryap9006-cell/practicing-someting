"""RailTwin-X Notification Center API Endpoints (Module I4).

Provides active notification querying, one-click acknowledgment, event emission,
and escalation ladder triggers for station operations.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import get_current_user, require_role
from data.audit import record_audit
from data.db import Database, get_db
from notifications.dispatcher import (
    acknowledge_notification,
    escalate_unacked_notifications,
    notify,
)

router = APIRouter(prefix="/api/notifications", tags=["Notification Center (I4)"])


class EmitNotificationRequest(BaseModel):
    event_type: str = Field(..., description="Event type code (e.g. PLATFORM_CHANGE, TSR_ACTIVE, CREW_BREACH)")
    target_roles: List[str] = Field(default_factory=lambda: ["station_master"], description="Target roles to receive alert")
    severity: str = Field("info", description="Severity: info, warning, critical")
    title: str = Field(..., description="Brief alert title")
    message: str = Field(..., description="Detailed alert body")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured event payload")
    station_code: str = Field("NDLS", description="Station code")


class AckNotificationRequest(BaseModel):
    channel: str = Field("in_app", description="Acknowledgment channel (in_app, whatsapp, sms)")
    notes: Optional[str] = Field(None, description="Optional ACK remarks")


class NotificationItem(BaseModel):
    id: int
    event_type: str
    target_role: Optional[str]
    severity: str
    title: str
    message: str
    payload_json: Optional[str]
    state: str
    created_at: str
    escalated_at: Optional[str] = None
    acked_at: Optional[str] = None
    acked_by: Optional[str] = None


@router.get("/active", response_model=List[NotificationItem])
def get_active_notifications(
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical)"),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Retrieves all active unacknowledged notifications relevant to the current user's role."""
    user_role = current_user.get("role_id", "viewer")
    
    query = """
        SELECT id, event_type, target_role, severity, title, message, payload_json, state,
               created_at, escalated_at, acked_at, acked_by
        FROM notifications
        WHERE state IN ('sent', 'escalated', 'queued')
    """
    params: List[Any] = []

    if user_role != "admin":
        query += " AND (target_role LIKE ? OR target_role = '*' OR target_role IS NULL)"
        params.append(f"%{user_role}%")

    if severity:
        query += " AND severity = ?"
        params.append(severity.lower())

    query += " ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    with db.transaction() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        NotificationItem(
            id=r["id"],
            event_type=r["event_type"],
            target_role=r["target_role"],
            severity=r["severity"],
            title=r["title"],
            message=r["message"],
            payload_json=r["payload_json"],
            state=r["state"],
            created_at=r["created_at"],
            escalated_at=r["escalated_at"],
            acked_at=r["acked_at"],
            acked_by=r["acked_by"],
        )
        for r in rows
    ]


@router.post("/{notification_id}/ack", response_model=Dict[str, Any])
def ack_notification_endpoint(
    notification_id: int,
    req: Optional[AckNotificationRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Marks an active notification as acknowledged with user identity and timestamp."""
    channel = req.channel if req else "in_app"
    notes = req.notes if req else ""

    try:
        res = acknowledge_notification(
            notif_id=notification_id,
            user_id=current_user["id"],
            channel=channel,
            notes=notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    record_audit(
        db_or_cursor=db,
        actor_id=current_user["id"],
        actor_role=current_user["role_id"],
        action="NOTIFICATION_ACKNOWLEDGED",
        table_name="notifications",
        record_id=notification_id,
        after_state={"acked_by": current_user["id"], "channel": channel},
    )

    return res


@router.post("/emit", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def emit_notification_endpoint(
    req: EmitNotificationRequest,
    current_user: Dict[str, Any] = Depends(
        require_role(["admin", "station_master", "dy_sm", "crew_controller", "section_controller", "engineer"])
    ),
    db: Database = Depends(get_db),
):
    """Emits an operational notification event to the central event bus."""
    result = notify(
        event_type=req.event_type,
        target_roles=req.target_roles,
        severity=req.severity,
        title=req.title,
        message=req.message,
        payload=req.payload,
        station_code=req.station_code,
        db=db,
    )

    record_audit(
        db_or_cursor=db,
        actor_id=current_user["id"],
        actor_role=current_user["role_id"],
        action="NOTIFICATION_EMITTED",
        table_name="notifications",
        record_id=result["notification_id"],
        after_state={"event_type": req.event_type, "severity": req.severity, "title": req.title},
    )

    return result


@router.post("/escalate", response_model=Dict[str, Any])
def trigger_escalation_ladder(
    max_age_minutes: int = Query(5, ge=1, le=60),
    current_user: Dict[str, Any] = Depends(require_role(["admin", "station_master"])),
    db: Database = Depends(get_db),
):
    """Triggers the escalation engine to escalate unacknowledged alerts older than max_age_minutes."""
    escalated = escalate_unacked_notifications(max_age_minutes=max_age_minutes, db=db)
    return {
        "status": "success",
        "escalated_count": len(escalated),
        "escalated_notifications": escalated,
    }
