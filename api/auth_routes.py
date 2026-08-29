"""RailTwin-X Authentication API Endpoints (Module I1).

Provides login, token refresh, and profile inspection endpoints.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import (
    create_access_token,
    get_current_user,
    verify_password,
)
from data.audit import record_audit
from data.db import Database, get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username (e.g. sm_ndls, admin)")
    password: str = Field(..., description="Plaintext password")


class UserProfile(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role_id: str
    role_name: str
    station_code: str
    full_name: str
    permissions_json: Optional[str] = "[]"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserProfile


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Database = Depends(get_db)):
    """Authenticates user credentials and issues a signed JWT access token."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.password_hash, u.role_id, u.station_code,
                   u.full_name, u.is_active, r.name as role_name, r.permissions_json
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ?;
            """,
            (request.username,),
        )
        row = cur.fetchone()

    if not row or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact system administrator.",
        )

    token_data = {
        "sub": row["username"],
        "user_id": row["id"],
        "role_id": row["role_id"],
        "station_code": row["station_code"],
    }
    access_token = create_access_token(data=token_data)

    user_profile = UserProfile(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        role_id=row["role_id"],
        role_name=row["role_name"],
        station_code=row["station_code"],
        full_name=row["full_name"],
        permissions_json=row["permissions_json"],
    )

    # Record login audit event
    record_audit(
        db_or_cursor=db,
        actor_id=row["id"],
        actor_role=row["role_id"],
        action="AUTH_LOGIN_SUCCESS",
        table_name="users",
        record_id=row["id"],
        after_state={"username": row["username"], "station_code": row["station_code"]},
    )

    return LoginResponse(access_token=access_token, user=user_profile)


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated user's profile and active permissions."""
    return UserProfile(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        role_id=current_user["role_id"],
        role_name=current_user["role_name"],
        station_code=current_user["station_code"],
        full_name=current_user["full_name"],
        permissions_json=current_user.get("permissions_json", "[]"),
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Refreshes the active JWT access token for the current session."""
    token_data = {
        "sub": current_user["username"],
        "user_id": current_user["id"],
        "role_id": current_user["role_id"],
        "station_code": current_user["station_code"],
    }
    new_token = create_access_token(data=token_data)
    user_profile = UserProfile(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        role_id=current_user["role_id"],
        role_name=current_user["role_name"],
        station_code=current_user["station_code"],
        full_name=current_user["full_name"],
        permissions_json=current_user.get("permissions_json", "[]"),
    )
    return LoginResponse(access_token=new_token, user=user_profile)
