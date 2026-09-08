"""Data access and service layer for system metadata, catalog pagination, and schema verification."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from data.db import Database


def get_paginated_stations(db: Database, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    """Returns a page of stations and total station count."""
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM stations")
        total = int(cur.fetchone()["count"])
        cur.execute(
            "SELECT code, name, is_junction, platforms, lat, lon FROM stations ORDER BY rowid ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return rows, total


def get_paginated_trains(db: Database, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    """Returns a page of trains and total train count."""
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM trains")
        total = int(cur.fetchone()["count"])
        cur.execute(
            "SELECT train_no, name, class, priority FROM trains ORDER BY priority ASC, train_no ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return rows, total


def get_schema_migration_count(db: Database) -> int:
    """Returns count of applied schema migrations."""
    with db.transaction() as cur:
        cur.execute("SELECT COUNT(*) AS count FROM schema_migrations")
        return int(cur.fetchone()["count"])
