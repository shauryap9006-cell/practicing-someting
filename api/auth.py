"""RailTwin-X Role-Based Access Control (RBAC) & Authentication Module (Module I1).

Provides secure JWT token management, PBKDF2 password hashing, and endpoint-level
FastAPI dependency role guards (default-deny policy).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from data.db import Database, get_db

SECRET_KEY = os.getenv("RAILTWIN_SECRET_KEY", "railtwin_dev_secret_key_sih_2026_super_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

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
            "ops:read", "ops:write", "ops:reoptimize", "ops:handover",
            "safety:read", "safety:write", "crew:read", "assets:read",
            "kpi:read", "notifications:ack"
        ],
    },
    "dy_sm": {
        "name": "Deputy Station Master (Dy.SM)",
        "description": "Operational shift supervisor, platform allocations, set-in/out logging, and incident recording.",
        "permissions": [
            "ops:read", "ops:write", "ops:handover",
            "safety:read", "safety:write", "crew:read", "notifications:ack"
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
        "permissions": ["ops:read", "ops:reoptimize", "safety:read", "safety:write", "notifications:ack"],
    },
    "engineer": {
        "name": "Station / Track Engineer",
        "description": "Asset registry maintenance, possession (PTW) workflows, work orders, and failure logging.",
        "permissions": ["assets:read", "assets:write", "safety:read", "safety:write", "notifications:ack"],
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
    """Hashes a plaintext password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored PBKDF2 hash."""
    try:
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
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT access token with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Database = Depends(get_db),
) -> Dict[str, Any]:
    """FastAPI dependency to extract and validate the authenticated user from the Authorization header."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name, u.is_active,
                   r.name as role_name, r.permissions_json
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ? AND u.is_active = 1;
            """,
            (username,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
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
