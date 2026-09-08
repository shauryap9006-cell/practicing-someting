"""RailTwin-X Authentication API Endpoints (Module I1).

Provides login, token refresh, and profile inspection endpoints.
"""

from __future__ import annotations

from engine.clocks import get_clock, now_iso, ist_now, IST_TIMEZONE

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from pydantic import BaseModel, Field

from api.auth import (
    KNOWN_PASSWORD_BLACKLIST,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    needs_rehash,
    security_bearer,
    verify_password,
)
from api.auth_limiter import (
    check_login_rate_limits,
    get_client_ip,
    record_login_failure,
    record_login_success,
    verify_dummy_password,
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
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=10, description="New password (minimum 10 characters)")


class ChangePasswordResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserProfile


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserProfile


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request, db: Database = Depends(get_db)):
    """Authenticates user credentials and issues a signed JWT access token."""
    client_ip = get_client_ip(http_request)
    username = request.username.strip()

    check_login_rate_limits(client_ip=client_ip, username=username)

    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.password_hash, u.role_id, u.station_code,
                   u.full_name, u.is_active, u.must_change_password, r.name as role_name, r.permissions_json
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE lower(u.username) = lower(?) OR lower(u.email) = lower(?);
            """,
            (username, username),
        )
        row = cur.fetchone()

    is_valid = False
    if row:
        is_valid = verify_password(request.password, row["password_hash"])
    else:
        verify_dummy_password(request.password)

    if not row or not is_valid:
        now_iso = get_clock().now_iso()
        record_login_failure(client_ip=client_ip, username=username, timestamp_iso=now_iso)
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

    record_login_success(username=username)

    if needs_rehash(row["password_hash"]):
        with db.transaction() as cur:
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(request.password), row["id"]),
            )

    must_change = bool(row["must_change_password"]) if "must_change_password" in row.keys() else False
    token_data = {
        "sub": row["username"],
        "user_id": row["id"],
        "role_id": row["role_id"],
        "station_code": row["station_code"],
        "must_change_password": must_change,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    refresh_payload = decode_refresh_token(refresh_token)
    now_iso = get_clock().now_iso()
    expires_iso = datetime.fromtimestamp(refresh_payload["exp"], tz=IST_TIMEZONE).isoformat()
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
        must_change_password=must_change,
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
        must_change_password=bool(current_user.get("must_change_password", False)),
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Changes user password, enforces password complexity and clears must_change_password flag."""
    with db.transaction() as cur:
        cur.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (current_user["id"],),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not verify_password(request.old_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_pw = request.new_password.strip()
    if len(new_pw) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 10 characters long.",
        )

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old password.",
        )

    if request.new_password in KNOWN_PASSWORD_BLACKLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password is too common or a known default. Please choose a stronger password.",
        )

    new_hash = hash_password(request.new_password)
    with db.transaction() as cur:
        cur.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 0
            WHERE id = ?
            """,
            (new_hash, current_user["id"]),
        )

    token_data = {
        "sub": current_user["username"],
        "user_id": current_user["id"],
        "role_id": current_user["role_id"],
        "station_code": current_user["station_code"],
        "must_change_password": False,
    }
    access_token = create_access_token(data=token_data)
    refresh_token_val = create_refresh_token(data=token_data)
    refresh_payload = decode_refresh_token(refresh_token_val)
    now_iso_val = ist_now().isoformat()
    expires_iso = datetime.fromtimestamp(refresh_payload["exp"], tz=IST_TIMEZONE).isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            INSERT INTO auth_sessions (token_id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                refresh_payload["jti"],
                current_user["id"],
                hashlib.sha256(refresh_token_val.encode("utf-8")).hexdigest(),
                now_iso_val,
                expires_iso,
            ),
        )

    user_profile = UserProfile(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        role_id=current_user["role_id"],
        role_name=current_user["role_name"],
        station_code=current_user["station_code"],
        full_name=current_user["full_name"],
        permissions_json=current_user.get("permissions_json", "[]"),
        must_change_password=False,
    )

    record_audit(
        db_or_cursor=db,
        actor_id=current_user["id"],
        actor_role=current_user["role_id"],
        action="AUTH_PASSWORD_CHANGE",
        table_name="users",
        record_id=current_user["id"],
        after_state={"username": current_user["username"], "must_change_password": 0},
    )

    return ChangePasswordResponse(
        message="Password updated successfully.",
        access_token=access_token,
        refresh_token=refresh_token_val,
        user=user_profile,
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
    now = ist_now()
    now_iso = now.isoformat()
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name,
                   u.is_active, u.must_change_password, r.name AS role_name, r.permissions_json
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

        must_change = bool(row["must_change_password"]) if "must_change_password" in row.keys() else False
        token_data = {
            "sub": row["username"],
            "user_id": row["id"],
            "role_id": row["role_id"],
            "station_code": row["station_code"],
            "must_change_password": must_change,
        }
        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data=token_data)
        new_payload = decode_refresh_token(new_refresh_token)
        new_expires_iso = datetime.fromtimestamp(new_payload["exp"], tz=IST_TIMEZONE).isoformat()
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
        must_change_password=must_change,
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
                    (now_iso(), payload["jti"]),
                )
        except HTTPException:
            pass
    return None
