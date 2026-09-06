"""RailTwin-X Authentication API Endpoints (Module I1).

Provides login, token refresh, and profile inspection endpoints.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from pydantic import BaseModel, Field

from api.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    needs_rehash,
    security_bearer,
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
    refresh_token: str
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
            WHERE lower(u.username) = lower(?) OR lower(u.email) = lower(?);
            """,
            (request.username.strip(), request.username.strip()),
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

    if needs_rehash(row["password_hash"]):
        with db.transaction() as cur:
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(request.password), row["id"]),
            )

    token_data = {
        "sub": row["username"],
        "user_id": row["id"],
        "role_id": row["role_id"],
        "station_code": row["station_code"],
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    refresh_payload = decode_refresh_token(refresh_token)
    now_iso = datetime.now(timezone.utc).isoformat()
    expires_iso = datetime.fromtimestamp(refresh_payload["exp"], timezone.utc).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO auth_sessions (token_id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                refresh_payload["jti"],
                row["id"],
                hashlib.sha256(refresh_token.encode("utf-8")).hexdigest(),
                now_iso,
                expires_iso,
            ),
        )

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

    return LoginResponse(access_token=access_token, refresh_token=refresh_token, user=user_profile)


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
def refresh_token(
    auth=Security(security_bearer),
    db: Database = Depends(get_db),
):
    """Rotates a server-tracked refresh token and issues a new access token."""
    if not auth or not auth.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required.")

    payload = decode_refresh_token(auth.credentials)
    token_hash = hashlib.sha256(auth.credentials.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name,
                   u.is_active, r.name AS role_name, r.permissions_json
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            JOIN roles r ON r.id = u.role_id
            WHERE s.token_id = ? AND s.token_hash = ? AND s.revoked_at IS NULL
              AND s.expires_at > ? AND u.is_active = 1
            LIMIT 1
            """,
            (payload["jti"], token_hash, now_iso),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is revoked or invalid.")

        token_data = {
            "sub": row["username"],
            "user_id": row["id"],
            "role_id": row["role_id"],
            "station_code": row["station_code"],
        }
        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data=token_data)
        new_payload = decode_refresh_token(new_refresh_token)
        new_expires_iso = datetime.fromtimestamp(new_payload["exp"], timezone.utc).isoformat()
        cur.execute(
            "UPDATE auth_sessions SET revoked_at = ?, replaced_by = ?, last_used_at = ? WHERE token_id = ?",
            (now_iso, new_payload["jti"], now_iso, payload["jti"]),
        )
        cur.execute(
            """
            INSERT INTO auth_sessions (token_id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                new_payload["jti"],
                row["id"],
                hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest(),
                now_iso,
                new_expires_iso,
            ),
        )

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
    return LoginResponse(access_token=new_access_token, refresh_token=new_refresh_token, user=user_profile)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth=Security(security_bearer), db: Database = Depends(get_db)):
    """Revokes the presented refresh token; replaying it cannot create a session."""
    if auth and auth.credentials:
        try:
            payload = decode_refresh_token(auth.credentials)
            with db.transaction() as cur:
                cur.execute(
                    "UPDATE auth_sessions SET revoked_at = COALESCE(revoked_at, ?) WHERE token_id = ?",
                    (datetime.now(timezone.utc).isoformat(), payload["jti"]),
                )
        except HTTPException:
            pass
    return None
