"""Operational advisories, track conflict scanning, and dispatch ACK webhook router."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import assert_station_scope, require_role
from api.brain import BrainOrchestrator
from api.schemas import DispatcherAckRequest, DispatcherAckResponse, WhatsAppWebhookResponse
from api.services.advisory_service import record_advisory_ack
from config import settings
from engine.conflicts import ConflictScanner
from notifications.health import get_health_tracker
from notifications.webhook_verify import verify_hmac

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/advise")
def post_brain_advise(
    payload: dict,
    current_user: dict = Depends(require_role(["station_master", "section_controller", "admin"])),
):
    """Executes the full perception -> ML inference -> Safety Interlock -> Conflict Scan pipeline."""
    train_no = payload.get("train_no")
    target_station = payload.get("target_station")
    if not train_no:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_TRAIN_NO", "message": "train_no is required in request payload", "retryable": False},
        )
    if target_station:
        assert_station_scope(current_user, str(target_station))

    orchestrator = BrainOrchestrator()
    return orchestrator.advise(train_no=str(train_no), target_station_code=target_station)


@router.get("/conflicts/{train_no}")
def get_train_conflicts(train_no: str):
    """Scans deterministic spatial track headway and single-line opposing conflicts for train_no."""
    scanner = ConflictScanner()
    conflicts = scanner.scan_train_conflicts(train_no)
    return {
        "train_no": train_no,
        "conflicts_count": len(conflicts),
        "conflicts": [c.to_dict() for c in conflicts],
        "human_ack_required": True,
    }


@router.post("/advise/{adv_id}/ack", response_model=DispatcherAckResponse)
def post_advisory_ack(
    adv_id: str,
    payload: DispatcherAckRequest,
    current_user: dict = Depends(require_role(["station_master", "dy_sm", "section_controller", "admin"])),
):
    """Records dispatcher acknowledgement (accept/reject) for an advisory.

    Stores the decision in the advisory_ack_log table for audit trail.
    Used by the frontend dispatcher interface to close the human-in-the-loop loop.
    """
    if payload.decision not in ("accepted", "rejected"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DECISION",
                "message": "decision must be 'accepted' or 'rejected'",
                "retryable": False,
            },
        )

    res = record_advisory_ack(
        adv_id=adv_id,
        decision=payload.decision,
        dispatcher_id=current_user["id"],
        comment=payload.comment,
        channel="web",
    )

    return DispatcherAckResponse(
        adv_id=res["adv_id"],
        decision=res["decision"],
        dispatcher_id=res["dispatcher_id"],
        comment=res["comment"],
        recorded_at=res["recorded_at"],
        status="ok",
    )


@router.post("/hooks/whatsapp", response_model=WhatsAppWebhookResponse)
async def whatsapp_inbound_webhook(request: Request):
    """Inbound webhook receiver from OpenWA gateway.

    Handles:
    1. session.status: updates WhatsApp gateway health status.
    2. message.received: parses 'ACK <id>' and 'ESC <id>' to close advisory loops.
    """
    body = await request.body()
    if not verify_hmac(body, request.headers, settings.OPENWA_WEBHOOK_SECRET, require_timestamp=True):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED_WEBHOOK", "message": "Invalid HMAC signature", "retryable": False},
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    event = (
        payload.get("event")
        or payload.get("type")
        or payload.get("event_type")
        or ""
    )

    health = get_health_tracker()

    # 1. Session status event
    if event == "session.status" or "status" in payload:
        status_val = payload.get("status") or payload.get("data", {}).get("status") or "unknown"
        health.set_whatsapp_status(status_val, event_type="session.status")
        return WhatsAppWebhookResponse(ok=True, event="session.status", action="status_updated")

    # 2. Inbound message event (Reply-to-ACK)
    raw_text = (
        payload.get("body")
        or payload.get("text")
        or payload.get("data", {}).get("body")
        or payload.get("data", {}).get("text")
        or ""
    )
    sender_raw = (
        payload.get("from")
        or payload.get("chatId")
        or payload.get("data", {}).get("from")
        or payload.get("data", {}).get("chatId")
        or ""
    )
    sender = sender_raw.split("@")[0].replace("+", "").strip()
    clean_text = raw_text.strip()
    upper_text = clean_text.upper()

    if upper_text.startswith("ACK ") or upper_text.startswith("ACCEPT "):
        adv_id = clean_text.split(" ", 1)[1].strip()
        record_advisory_ack(
            adv_id=adv_id,
            decision="accepted",
            dispatcher_id=sender or "WHATSAPP-USER",
            comment=f"Accepted via WhatsApp ({sender})",
            channel="whatsapp",
        )
        return WhatsAppWebhookResponse(
            ok=True,
            event="message.received",
            action="accepted",
            adv_id=adv_id,
            sender=sender,
        )
    elif upper_text.startswith("ESC ") or upper_text.startswith("REJ ") or upper_text.startswith("REJECT "):
        adv_id = clean_text.split(" ", 1)[1].strip()
        record_advisory_ack(
            adv_id=adv_id,
            decision="rejected",
            dispatcher_id=sender or "WHATSAPP-USER",
            comment=f"Escalated/Rejected via WhatsApp ({sender})",
            channel="whatsapp",
        )
        return WhatsAppWebhookResponse(
            ok=True,
            event="message.received",
            action="rejected",
            adv_id=adv_id,
            sender=sender,
        )

    return WhatsAppWebhookResponse(
        ok=True,
        event=event or "unhandled",
        action="ignored",
        sender=sender,
    )
