"""Public access-request intake for prospective RailTwin-X operators."""

from __future__ import annotations

from engine.clocks import now_iso

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from data.db import Database, get_db


router = APIRouter(prefix="/api/access-requests", tags=["Access Requests"])


class AccessRequestPayload(BaseModel):
    station_code: str = Field(..., min_length=2, max_length=8, pattern=r"^[A-Za-z0-9_-]+$")
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    organization: str | None = Field(default=None, max_length=160)


class AccessRequestResponse(BaseModel):
    request_id: str
    status: str
    requested_at: str


@router.post("", response_model=AccessRequestResponse, status_code=201)
def create_access_request(
    payload: AccessRequestPayload,
    db: Database = Depends(get_db),
):
    request_id = uuid4().hex
    requested_at = now_iso()
    email = payload.email.strip().lower()
    with db.transaction() as cur:
        # Idempotent intake: a pending request for the same email is returned
        # instead of creating another row (prevents unauthenticated table spam).
        cur.execute(
            "SELECT request_id, requested_at FROM access_requests WHERE email = ? AND status = 'pending' LIMIT 1",
            (email,),
        )
        existing = cur.fetchone()
        if existing:
            return AccessRequestResponse(
                request_id=existing["request_id"], status="pending", requested_at=existing["requested_at"]
            )
        cur.execute(
            """
            INSERT INTO access_requests
              (request_id, station_code, full_name, email, organization, requested_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                payload.station_code.upper(),
                payload.full_name.strip(),
                email,
                payload.organization.strip() if payload.organization else None,
                requested_at,
            ),
        )
    return AccessRequestResponse(request_id=request_id, status="pending", requested_at=requested_at)
