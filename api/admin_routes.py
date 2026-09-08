"""RailTwin-X Administration API Endpoints (Module I1 & I5).

Provides user administration, role assignment, database backup execution, and restore verification.
All administrative actions are gated by role 'admin' and strictly audited.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from api.auth import hash_password, require_role
from config import settings
from data.audit import record_audit
from data.db import Database, get_db
from engine.clocks import get_clock, now_iso
from scripts.backup_db import BACKUPS_DIR, create_database_backup, verify_backup_file

router = APIRouter(prefix="/api/admin", tags=["Administration & Governance"])

_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
_STATION_PATTERN = re.compile(r"^[A-Z0-9_-]{2,8}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    email = value.strip().lower()
    if not email:
        return None
    if len(email) > 254 or not _EMAIL_PATTERN.fullmatch(email):
        raise ValueError("email must be a valid address")
    return email


def _normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "username must be 3-64 chars of lowercase letters, digits, '.', '_' or '-'"
        )
    return username


def _normalize_station(value: str) -> str:
    station = value.strip().upper()
    if not _STATION_PATTERN.fullmatch(station):
        raise ValueError("station_code must be a 2-8 character alphanumeric code")
    return station


def _validate_password(value: str) -> str:
    if len(value) < settings.MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
    if value.strip() != value:
        raise ValueError("password must not start or end with whitespace")
    return value


class CreateUserRequest(BaseModel):
    username: str = Field(..., description="Unique username")
    email: Optional[str] = Field(None, description="Contact email")
    password: str = Field(..., description="Plaintext password")
    role_id: str = Field(..., description="Role ID (e.g. station_master, dy_sm, engineer)")
    station_code: str = Field(
        default_factory=lambda: settings.DEFAULT_STATION_CODE, description="Station code assignment"
    )
    full_name: str = Field(..., min_length=2, max_length=120, description="Full display name")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _normalize_username(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_email(v)

    @field_validator("station_code")
    @classmethod
    def validate_station(cls, v: str) -> str:
        return _normalize_station(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    role_id: Optional[str] = None
    station_code: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    is_active: Optional[bool] = None
    new_password: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_email(v)

    @field_validator("station_code")
    @classmethod
    def validate_station(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_station(v) if v is not None else None

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        return _validate_password(v) if v is not None else None


class UserDetailResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    role_id: str
    role_name: str
    station_code: str
    full_name: str
    is_active: bool
    created_at: str


class BackupRecord(BaseModel):
    id: int
    filename: str
    backup_ts: str
    size_bytes: int
    row_counts_json: Optional[str]
    status: str
    checksum_sha256: str


class AccessRequestReview(BaseModel):
    status: Literal["approved", "rejected"]


class AccessRequestRecord(BaseModel):
    request_id: str
    station_code: str
    full_name: str
    email: str
    organization: Optional[str]
    status: str
    requested_at: str
    reviewed_at: Optional[str]
    reviewed_by: Optional[str]


@router.get("/access-requests", response_model=List[AccessRequestRecord])
def list_access_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Lists bounded access requests for administrator review."""
    query = "SELECT * FROM access_requests WHERE 1=1"
    params: List[Any] = []
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter.lower())
    query += " ORDER BY requested_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with db.transaction() as cur:
        cur.execute(query, tuple(params))
        return [AccessRequestRecord(**dict(row)) for row in cur.fetchall()]


@router.put("/access-requests/{request_id}", response_model=AccessRequestRecord)
def review_access_request(
    request_id: str,
    req: AccessRequestReview,
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Approves or rejects an access request without silently provisioning an account."""
    reviewed_at = now_iso()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM access_requests WHERE request_id = ?", (request_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found."
            )
        cur.execute(
            """
            UPDATE access_requests
            SET status = ?, reviewed_at = ?, reviewed_by = ?
            WHERE request_id = ?
            """,
            (req.status, reviewed_at, admin_user["id"], request_id),
        )
        record_audit(
            db_or_cursor=cur,
            actor_id=admin_user["id"],
            actor_role=admin_user["role_id"],
            action="ACCESS_REQUEST_REVIEWED",
            table_name="access_requests",
            record_id=request_id,
            before_state={"status": existing["status"]},
            after_state={"status": req.status},
        )
        cur.execute("SELECT * FROM access_requests WHERE request_id = ?", (request_id,))
        return AccessRequestRecord(**dict(cur.fetchone()))


@router.get("/users", response_model=List[UserDetailResponse])
def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Lists all registered users in the station operating system."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name,
                   u.is_active, u.created_at, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

    return [
        UserDetailResponse(
            id=r["id"],
            username=r["username"],
            email=r["email"],
            role_id=r["role_id"],
            role_name=r["role_name"],
            station_code=r["station_code"],
            full_name=r["full_name"],
            is_active=bool(r["is_active"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/users", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    req: CreateUserRequest,
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Creates a new user account and writes an audited record."""
    user_id = f"usr-{req.username}-{uuid4().hex[:8]}"
    now_iso = get_clock().now_iso()
    pwd_hash = hash_password(req.password)
    email = req.email

    with db.transaction() as cur:
        cur.execute("SELECT id, name FROM roles WHERE id = ?;", (req.role_id,))
        role_row = cur.fetchone()
        if not role_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role_id '{req.role_id}'.",
            )
        role_name = role_row["name"]

        # Login is case-insensitive on username/email, so uniqueness must be too.
        cur.execute("SELECT id FROM users WHERE lower(username) = ?;", (req.username,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{req.username}' already exists.",
            )
        if email:
            cur.execute("SELECT id FROM users WHERE lower(email) = ?;", (email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
                )

        cur.execute(
            """
            INSERT INTO users (id, username, email, password_hash, role_id, station_code, full_name, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
            """,
            (
                user_id,
                req.username,
                email,
                pwd_hash,
                req.role_id,
                req.station_code,
                req.full_name,
                now_iso,
            ),
        )
        cur.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?);",
            (user_id, req.role_id),
        )

        record_audit(
            db_or_cursor=cur,
            actor_id=admin_user["id"],
            actor_role=admin_user["role_id"],
            action="USER_CREATED",
            table_name="users",
            record_id=user_id,
            after_state={
                "username": req.username,
                "role_id": req.role_id,
                "station_code": req.station_code,
            },
        )

    return UserDetailResponse(
        id=user_id,
        username=req.username,
        email=email,
        role_id=req.role_id,
        role_name=role_name,
        station_code=req.station_code,
        full_name=req.full_name,
        is_active=True,
        created_at=now_iso,
    )


@router.put("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Updates user attributes (role, station code, active state, or password) with audit logging."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.email, u.role_id, u.station_code, u.full_name,
                   u.is_active, u.created_at, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?;
            """,
            (user_id,),
        )
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        before_state = {
            "email": existing["email"],
            "role_id": existing["role_id"],
            "station_code": existing["station_code"],
            "full_name": existing["full_name"],
            "is_active": existing["is_active"],
        }

        new_email = req.email if req.email is not None else existing["email"]
        new_role = req.role_id if req.role_id is not None else existing["role_id"]
        new_station = req.station_code if req.station_code is not None else existing["station_code"]
        new_name = req.full_name if req.full_name is not None else existing["full_name"]
        new_active = int(req.is_active) if req.is_active is not None else existing["is_active"]

        if req.role_id is not None:
            cur.execute("SELECT id FROM roles WHERE id = ?;", (req.role_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role_id '{req.role_id}'.",
                )

        if req.email is not None and new_email != existing["email"]:
            cur.execute(
                "SELECT id FROM users WHERE lower(email) = ? AND id != ?;", (new_email, user_id)
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
                )

        # Guard against an administrator locking themselves (and possibly everyone) out.
        if user_id == admin_user["id"]:
            if not new_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot deactivate your own account.",
                )
            if new_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot remove your own admin role.",
                )

        if req.new_password:
            new_pwd_hash = hash_password(req.new_password)
            cur.execute(
                """
                UPDATE users SET email = ?, role_id = ?, station_code = ?, full_name = ?, is_active = ?, password_hash = ?
                WHERE id = ?;
                """,
                (new_email, new_role, new_station, new_name, new_active, new_pwd_hash, user_id),
            )
        else:
            cur.execute(
                """
                UPDATE users SET email = ?, role_id = ?, station_code = ?, full_name = ?, is_active = ?
                WHERE id = ?;
                """,
                (new_email, new_role, new_station, new_name, new_active, user_id),
            )

        if req.role_id:
            cur.execute("UPDATE user_roles SET role_id = ? WHERE user_id = ?;", (new_role, user_id))

        cur.execute("SELECT name FROM roles WHERE id = ?;", (new_role,))
        role_row = cur.fetchone()
        role_name = role_row["name"] if role_row else new_role

        after_state = {
            "email": new_email,
            "role_id": new_role,
            "station_code": new_station,
            "full_name": new_name,
            "is_active": new_active,
        }

        record_audit(
            db_or_cursor=cur,
            actor_id=admin_user["id"],
            actor_role=admin_user["role_id"],
            action="USER_UPDATED",
            table_name="users",
            record_id=user_id,
            before_state=before_state,
            after_state=after_state,
        )

    return UserDetailResponse(
        id=user_id,
        username=existing["username"],
        email=new_email,
        role_id=new_role,
        role_name=role_name,
        station_code=new_station,
        full_name=new_name,
        is_active=bool(new_active),
        created_at=existing["created_at"],
    )


@router.get("/backups", response_model=List[BackupRecord])
def list_backups(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Lists all automated and on-demand database backup snapshots."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT id, filename, backup_ts, size_bytes, row_counts_json, status, checksum_sha256
            FROM backups
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

    return [
        BackupRecord(
            id=r["id"],
            filename=r["filename"],
            backup_ts=r["backup_ts"],
            size_bytes=r["size_bytes"],
            row_counts_json=r["row_counts_json"],
            status=r["status"],
            checksum_sha256=r["checksum_sha256"],
        )
        for r in rows
    ]


@router.post("/backups/create", response_model=Dict[str, Any])
def trigger_backup(
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Triggers an immediate WAL-safe SQLite database backup."""
    result = create_database_backup(db=db, tag="manual")
    record_audit(
        db_or_cursor=db,
        actor_id=admin_user["id"],
        actor_role=admin_user["role_id"],
        action="BACKUP_CREATED",
        table_name="backups",
        record_id=result["id"],
        after_state={"filename": result["filename"], "checksum": result["checksum_sha256"]},
    )
    return result


@router.post("/backups/verify", response_model=Dict[str, Any])
def verify_latest_backup(
    admin_user: Dict[str, Any] = Depends(require_role("admin")),
    db: Database = Depends(get_db),
):
    """Verifies the integrity of the most recent database backup file."""
    with db.transaction() as cur:
        cur.execute("SELECT filename FROM backups ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No backup records found."
        )

    backup_path = BACKUPS_DIR / row["filename"]
    if not backup_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file '{row['filename']}' missing on disk.",
        )

    verification = verify_backup_file(backup_path)
    return {
        "filename": row["filename"],
        "verification": verification,
    }
