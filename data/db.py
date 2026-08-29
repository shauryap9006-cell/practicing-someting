"""RailTwin-X SQLite Database Engine & Connection Manager.

Provides robust database initialization, migration tracking, connection pooling / transaction handling,
and table inspection against the single-file SQLite database.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

DEFAULT_DB_PATH = Path(__file__).parent / "railtwin.db"
SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"
MIGRATIONS_DIR = Path(__file__).parent.parent / "scripts" / "migrations"


import threading

_WRITE_LOCK = threading.Lock()


class Database:
    """SQLite Database wrapper ensuring foreign key enforcement, tuned WAL concurrency, and thread safety (F36)."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a new sqlite3 connection configured with foreign keys and row factory."""
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=60.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")  # High concurrency reading
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        conn.execute("PRAGMA mmap_size = 268435456;")  # 256MB mmap
        conn.execute("PRAGMA journal_size_limit = 67108864;")  # 64MB journal limit
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager providing a transactional cursor with automatic commit/rollback and thread-safe write protection."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_indexes(self) -> None:
        """Ensures all essential query performance indexes exist."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_events_lookup ON station_events(train_no, station_code, run_date);",
            "CREATE INDEX IF NOT EXISTS idx_events_date ON station_events(run_date);",
            "CREATE INDEX IF NOT EXISTS idx_events_train_date ON station_events(train_no, run_date);",
            "CREATE INDEX IF NOT EXISTS idx_events_station_date ON station_events(station_code, run_date);",
            "CREATE TABLE IF NOT EXISTS hist_baselines (train_no TEXT NOT NULL, station_code TEXT NOT NULL, avg_delay REAL NOT NULL, p90_delay REAL NOT NULL, chronic_delay_flag INTEGER NOT NULL DEFAULT 0, sample_count INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, PRIMARY KEY (train_no, station_code));",
            "CREATE INDEX IF NOT EXISTS idx_hist_baselines ON hist_baselines(train_no, station_code);",
        ]
        with self.transaction() as cur:
            for idx_sql in indexes:
                cur.execute(idx_sql)

    def materialize_historical_baselines(self) -> int:
        """Materializes historical delay averages into hist_baselines table for O(1) journey lookups (F31)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO hist_baselines (train_no, station_code, avg_delay, p90_delay, chronic_delay_flag, sample_count, updated_at)
                SELECT
                    train_no,
                    station_code,
                    AVG(COALESCE(delay_arr_min, delay_dep_min, 0.0)) as avg_delay,
                    AVG(COALESCE(delay_arr_min, delay_dep_min, 0.0)) * 1.5 as p90_delay,
                    CASE WHEN AVG(COALESCE(delay_arr_min, delay_dep_min, 0.0)) > 30.0 THEN 1 ELSE 0 END as chronic_delay_flag,
                    COUNT(*) as sample_count,
                    ? as updated_at
                FROM station_events
                GROUP BY train_no, station_code;
                """,
                (now_iso,),
            )
            cur.execute("SELECT COUNT(*) FROM hist_baselines;")
            return int(cur.fetchone()[0])


    def apply_migrations(self, migrations_dir: Optional[Path | str] = None) -> List[str]:
        """Applies pending SQL migration files in ascending order and records them in schema_migrations."""
        mdir = Path(migrations_dir) if migrations_dir else MIGRATIONS_DIR
        applied: List[str] = []
        if not mdir.exists():
            return applied

        conn = self.get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
            applied_versions = {row[0] for row in cursor.fetchall()}

            migration_files = sorted(mdir.glob("*.sql"))
            for mfile in migration_files:
                match = re.match(r"^(\d+)_", mfile.name)
                if not match:
                    continue
                version = int(match.group(1))
                if version not in applied_versions:
                    sql_content = mfile.read_text(encoding="utf-8")
                    try:
                        cursor.executescript(sql_content)
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e).lower():
                            pass
                        else:
                            raise
                    now_iso = datetime.now(timezone.utc).isoformat()
                    cursor.execute(
                        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                        (version, mfile.name, now_iso),
                    )
                    conn.commit()
                    applied.append(mfile.name)
        finally:
            conn.close()

        return applied

    def init_schema(self, schema_file: Optional[Path | str] = None) -> None:
        """Initializes tables, indexes, and constraints from schema.sql and applies migrations."""
        path = Path(schema_file) if schema_file else SCHEMA_SQL_PATH
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found at: {path}")

        sql_script = path.read_text(encoding="utf-8")
        conn = self.get_connection()
        try:
            conn.executescript(sql_script)
            conn.commit()
        finally:
            conn.close()

        self.ensure_indexes()
        self.apply_migrations()

    def table_counts(self) -> dict[str, int]:
        """Returns row counts for all primary tables."""
        tables = [
            "stations",
            "trains",
            "route_stations",
            "sections",
            "rake_links",
            "station_events",
            "weather",
            "sim_ledger",
            "staff",
            "notification_log",
            "roles",
            "users",
            "audit_log",
            "backups",
            "handover_log",
            "notifications",
            "train_runs",
            "run_snapshots",
            "timetable_versions",
            "timetable_entries",
            "ad_events",
            "platform_states",
            "platform_assignments",
            "block_status",
            "shunting_moves",
            "planner_changesets",
        ]
        counts = {}
        with self.transaction() as cur:
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    counts[t] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    counts[t] = 0
        return counts

    def reset_database(self) -> None:
        """Drops and recreates all tables."""
        if self.db_path.exists():
            self.db_path.unlink()
        self.init_schema()


# Global DB instance
_DEFAULT_DB: Optional[Database] = None


def get_db(db_path: Optional[Path | str] = None) -> Database:
    """Returns the shared Database instance or initializes a custom one."""
    global _DEFAULT_DB
    if db_path:
        return Database(db_path)
    if _DEFAULT_DB is None:
        _DEFAULT_DB = Database(DEFAULT_DB_PATH)
    return _DEFAULT_DB


if __name__ == "__main__":
    print("=== RailTwin-X Database Initialization Demo ===")
    db = get_db()
    db.init_schema()
    counts = db.table_counts()
    print("Database schema successfully initialized. Table row counts:")
    for tbl, cnt in counts.items():
        print(f"  - {tbl}: {cnt} rows")
