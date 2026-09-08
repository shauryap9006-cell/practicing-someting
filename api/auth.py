"""RailTwin-X Role-Based Access Control (RBAC) & Authentication Module (Module I1).

Provides secure JWT token management, Argon2id password hashing, and endpoint-level
FastAPI dependency role guards (default-deny policy).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Sequence, Union
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from data.db import Database, get_db
from engine.clocks import RealClock

# Insecure known/demo passwords disallowed during password change (SEC-004)
KNOWN_PASSWORD_BLACKLIST = {
    "RailTwinAdmin2026!",
    "StationMaster2026!",
    "DyStationMaster2026!",
    "CrewController2026!",
    "SectionController2026!",
    "TrackEngineer2026!",
    "TTEOfficer2026!",
    "CommercialInsp2026!",
    "ViewerGuest2026!",
    "StationMasterCNB2026!",
    "password1234",
    "admin123456",
    "password123",
}

if settings.ENV.strip().lower() == "production" and len(settings.JWT_SECRET_KEY.strip()) < 32:
    raise RuntimeError("RAILTWIN_JWT_SECRET_KEY must be configured before starting in production")

# Development/test processes get an ephemeral key rather than a known reusable secret.
# Production is rejected above and by Settings.validate_runtime_safety when no key is set.
SECRET_KEY = settings.JWT_SECRET_KEY.strip() or secrets.token_urlsafe(48)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

security_bearer = HTTPBearer(auto_error=False)

# 9 Standard Indian Railways Station OS Roles
STANDARD_ROLES = {
    "admin": {
        "name": "System Administrator",
        "description": "Full administrative control, user management, backups, and audit verification.",
        "permissions": ["*"],
    },
    "station_master": {
        "name": "Station Master (SM)",
        "description": "Supreme operational command over station, Gantt re-optimization, shift handover, and safety interlocks.",
        "permissions": [
            "ops:read",
            "ops:write",
            "ops:reoptimize",
            "ops:handover",
            "safety:read",
            "safety:write",
            "crew:read",
            "assets:read",
            "kpi:read",
            "notifications:ack",
        ],
    },
    "dy_sm": {
        "name": "Deputy Station Master (Dy.SM)",
        "description": "Operational shift supervisor, platform allocations, set-in/out logging, and incident recording.",
        "permissions": [
            "ops:read",
            "ops:write",
            "ops:handover",
            "safety:read",
            "safety:write",
            "crew:read",
            "notifications:ack",
        ],
    },
    "crew_controller": {
        "name": "Crew Controller",
        "description": "Crew rostering, duty breach alerts, sign-on/sign-off tracking, and leave management.",
        "permissions": ["crew:read", "crew:write", "ops:read", "notifications:ack"],
    },
    "section_controller": {
        "name": "Section Controller",
        "description": "Corridor block line clearance, speed restrictions (TSRs), and inter-station scheduling.",
        "permissions": [
            "ops:read",
            "ops:reoptimize",
            "safety:read",
            "safety:write",
            "notifications:ack",
        ],
    },
    "engineer": {
        "name": "Station / Track Engineer",
        "description": "Asset registry maintenance, possession (PTW) workflows, work orders, and failure logging.",
        "permissions": [
            "assets:read",
            "assets:write",
            "safety:read",
            "safety:write",
            "notifications:ack",
        ],
    },
    "tte": {
        "name": "Train Ticket Examiner (TTE)",
        "description": "Passenger status inspection, onboard incidents, and coach occupancy tracking.",
        "permissions": ["passenger:read", "passenger:write", "ops:read"],
    },
    "commercial_inspector": {
        "name": "Commercial Inspector",
        "description": "Station footfall, commercial earnings, vendor lease management, and parcel tracking.",
        "permissions": ["commercial:read", "commercial:write", "kpi:read"],
    },
    "viewer": {
        "name": "Read-Only Viewer",
        "description": "Public station boards, live GIS corridor map view, and KPI read access.",
        "permissions": ["ops:read", "safety:read", "kpi:read"],
    },
}


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a plaintext password with memory-hard Argon2id.

    ``salt`` is retained only for source compatibility with the old helper. Argon2
    generates and stores a cryptographically random salt in its encoded hash.
    """
    if not password:
        raise ValueError("Password must not be empty")
    return PASSWORD_HASHER.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies Argon2id hashes and accepts legacy PBKDF2 only for migration."""
    try:
        if hashed_password.startswith("$argon2"):
            return PASSWORD_HASHER.verify(hashed_password, plain_password)

        # Legacy hashes are accepted during login so existing accounts can be
        # transparently upgraded by auth_routes.login; new hashes are Argon2id.
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return secrets.compare_digest(key.hex(), expected_hex)
    except (InvalidHashError, VerificationError, VerifyMismatchError, ValueError, TypeError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Returns whether a stored password should be upgraded on successful login."""
    if not hashed_password.startswith("$argon2"):
        return True
    try:
        return PASSWORD_HASHER.check_needs_rehash(hashed_password)
    except (InvalidHashError, VerificationError, ValueError, TypeError):
        return True


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT access token with expiration."""
    to_encode = data.copy()
    now = RealClock().now()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jti": to_encode.get("jti", str(uuid4())),
            "typ": "access",
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Creates a rotating, server-revocable refresh token."""
    now = RealClock().now()
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": now,
            "jti": str(uuid4()),
            "typ": "refresh",
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ", "access") != "access" or not payload.get("sub"):
            raise jwt.InvalidTokenError("not an access token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Decodes a refresh token and rejects access-token substitution."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "refresh" or not payload.get("sub") or not payload.get("jti"):
            raise jwt.InvalidTokenError("not a refresh token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Database = Depends(get_db),
    request: Request = None,  # type: ignore[assignment]
) -> Dict[str, Any]:
    """FastAPI dependency to extract and validate the authenticated user from the Authorization header."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    username = payload["sub"]

    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name, u.is_active,
                   u.must_change_password,
                   r.name as role_name, r.permissions_json
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ? AND u.is_active = 1
            LIMIT 1;
            """,
            (username,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_must_change = bool(payload.get("must_change_password", False))
    if token_must_change:
        path = request.url.path if request is not None else ""
        if not path.startswith("/api/auth/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required. You must change your temporary password at /api/auth/change-password before accessing system resources.",
            )

    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role_id": row["role_id"],
        "role_name": row["role_name"],
        "station_code": row["station_code"],
        "full_name": row["full_name"],
        "permissions_json": row["permissions_json"],
        "must_change_password": bool(row["must_change_password"])
        if "must_change_password" in row.keys()
        else False,
    }


def require_role(allowed_roles: Union[str, Sequence[str]]):
    """Factory creating a FastAPI dependency requiring one of the specified roles."""
    if isinstance(allowed_roles, str):
        roles_set = {allowed_roles}
    else:
        roles_set = set(allowed_roles)

    # Always allow admin
    roles_set.add("admin")

    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role_id")
        if user_role not in roles_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user_role}' is not authorized. Allowed roles: {sorted(list(roles_set))}",
            )
        return current_user

    return role_checker


def assert_station_scope(current_user: Dict[str, Any], station_code: str) -> None:
    """Reject station-scoped mutations outside the operator's assigned station."""
    role = current_user.get("role_id")
    if role in {"admin", "section_controller"}:
        return
    assigned = str(current_user.get("station_code") or "").strip().upper()
    requested = str(station_code or "").strip().upper()
    if not assigned or not requested or assigned != requested:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "STATION_SCOPE_DENIED",
                "message": "This account is not authorized for the requested station.",
                "retryable": False,
            },
        )


def effective_station_scope(
    current_user: Dict[str, Any], requested_station: Optional[str] = None
) -> Optional[str]:
    """Returns the permitted station filter, or ``None`` for global roles."""
    requested = str(requested_station or "").strip().upper() or None
    if current_user.get("role_id") in {"admin", "section_controller"}:
        return requested

    assigned = str(current_user.get("station_code") or "").strip().upper() or None
    if requested and requested != assigned:
        assert_station_scope(current_user, requested)
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "STATION_SCOPE_MISSING",
                "message": "This account has no assigned station scope.",
                "retryable": False,
            },
        )
    return assigned
