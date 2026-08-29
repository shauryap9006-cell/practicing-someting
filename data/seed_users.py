"""RailTwin-X Seed Users & Roles Provisioning (Module I1).

Populates the 9 standard Indian Railways roles and default operational accounts with
cryptographically secure password hashes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from api.auth import STANDARD_ROLES, hash_password
from data.db import Database, get_db

DEFAULT_USERS = [
    {
        "id": "usr-admin-01",
        "username": "admin",
        "email": "admin@railtwin.internal",
        "password": "RailTwinAdmin2026!",
        "role_id": "admin",
        "station_code": "NDLS",
        "full_name": "Chief System Administrator",
    },
    {
        "id": "usr-sm-ndls-01",
        "username": "sm_ndls",
        "email": "sm@ndls.railnet.gov.in",
        "password": "StationMaster2026!",
        "role_id": "station_master",
        "station_code": "NDLS",
        "full_name": "Rajesh Kumar (Station Master NDLS)",
    },
    {
        "id": "usr-dysm-ndls-01",
        "username": "dysm_ndls",
        "email": "dysm@ndls.railnet.gov.in",
        "password": "DyStationMaster2026!",
        "role_id": "dy_sm",
        "station_code": "NDLS",
        "full_name": "Amitabh Sharma (Dy. SM Ops)",
    },
    {
        "id": "usr-crew-ctrl-01",
        "username": "crew_ctrl",
        "email": "crew@delhi.railnet.gov.in",
        "password": "CrewController2026!",
        "role_id": "crew_controller",
        "station_code": "NDLS",
        "full_name": "Suresh Raina (Crew Controller Northern Zone)",
    },
    {
        "id": "usr-section-ctrl-01",
        "username": "section_ctrl",
        "email": "controller@cnb.railnet.gov.in",
        "password": "SectionController2026!",
        "role_id": "section_controller",
        "station_code": "CNB",
        "full_name": "Vikram Seth (Section Controller Cawnpore)",
    },
    {
        "id": "usr-eng-01",
        "username": "engineer_track",
        "email": "pway@ndls.railnet.gov.in",
        "password": "TrackEngineer2026!",
        "role_id": "engineer",
        "station_code": "NDLS",
        "full_name": "Er. Priya Patel (Senior Section Engineer P-Way)",
    },
    {
        "id": "usr-tte-01",
        "username": "tte_rajdhani",
        "email": "tte@nr.railnet.gov.in",
        "password": "TTEOfficer2026!",
        "role_id": "tte",
        "station_code": "NDLS",
        "full_name": "Manoj Tiwari (Head TTE Delhi Division)",
    },
    {
        "id": "usr-comm-01",
        "username": "comm_inspector",
        "email": "commercial@lko.railnet.gov.in",
        "password": "CommercialInsp2026!",
        "role_id": "commercial_inspector",
        "station_code": "LKO",
        "full_name": "Ananya Roy (Commercial Inspector Lucknow)",
    },
    {
        "id": "usr-viewer-01",
        "username": "viewer",
        "email": "viewer@railtwin.internal",
        "password": "ViewerGuest2026!",
        "role_id": "viewer",
        "station_code": "NDLS",
        "full_name": "Public Operations Observer",
    },
    {
        "id": "usr-sm-cnb-01",
        "username": "sm_cnb",
        "email": "sm@cnb.railnet.gov.in",
        "password": "StationMasterCNB2026!",
        "role_id": "station_master",
        "station_code": "CNB",
        "full_name": "Dinesh Gupta (Station Master Kanpur Central)",
    },
]


def seed_roles_and_users(db: Optional[Database] = None) -> dict[str, int]:
    """Seeds the standard roles and users into the database idempotently."""
    database = db or get_db()
    database.init_schema()
    now_iso = datetime.now(timezone.utc).isoformat()

    roles_count = 0
    users_count = 0

    with database.transaction() as cur:
        # 1. Seed Roles
        for role_id, meta in STANDARD_ROLES.items():
            cur.execute(
                """
                INSERT INTO roles (id, name, description, permissions_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    permissions_json = excluded.permissions_json;
                """,
                (
                    role_id,
                    meta["name"],
                    meta["description"],
                    json.dumps(meta["permissions"]),
                ),
            )
            roles_count += 1

        # 2. Seed Users
        for u in DEFAULT_USERS:
            pwd_hash = hash_password(u["password"])
            cur.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role_id, station_code, full_name, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(username) DO UPDATE SET
                    email = excluded.email,
                    role_id = excluded.role_id,
                    station_code = excluded.station_code,
                    full_name = excluded.full_name;
                """,
                (
                    u["id"],
                    u["username"],
                    u["email"],
                    pwd_hash,
                    u["role_id"],
                    u["station_code"],
                    u["full_name"],
                    now_iso,
                ),
            )
            
            # Map user_roles
            cur.execute(
                """
                INSERT OR IGNORE INTO user_roles (user_id, role_id)
                VALUES (?, ?);
                """,
                (u["id"], u["role_id"]),
            )
            users_count += 1

    return {"roles_seeded": roles_count, "users_seeded": users_count}


if __name__ == "__main__":
    print("=== Seeding RailTwin-X Roles & Standard Users ===")
    res = seed_roles_and_users()
    print(f"Success: Seeded {res['roles_seeded']} roles and {res['users_seeded']} operational accounts.")
