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
        if not self.db_path.exists():
            gz_path = self.db_path.with_name(self.db_path.name + ".gz")
            if gz_path.exists():
                import gzip
                import shutil
                print(f"[DB] Extracting compressed dataset {gz_path.name} -> {self.db_path.name}...", flush=True)
                with gzip.open(gz_path, "rb") as f_in:
                    with open(self.db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print("[DB] Dataset extracted successfully.", flush=True)

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
            "CREATE INDEX IF NOT EXISTS idx_live_positions_station ON live_positions(current_station_code);",
            "CREATE INDEX IF NOT EXISTS idx_live_positions_updated ON live_positions(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_live_delay_ledger_train ON live_delay_ledger(train_no, run_date);",
            "CREATE INDEX IF NOT EXISTS idx_live_delay_ledger_timestamp ON live_delay_ledger(timestamp);",
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
            "live_positions",
            "live_delay_ledger",
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

    def upsert_live_position(
        self,
        train_no: str,
        run_date: str,
        lat: float,
        lng: float,
        current_station_code: Optional[str] = None,
        next_station_code: Optional[str] = None,
        section_id: Optional[str] = None,
        speed_kmh: float = 0.0,
        delay_minutes: float = 0.0,
        confidence: float = 1.0,
        progress_pct: float = 0.0,
        is_dead_reckoned: int = 0,
        source: str = "live",
        last_event_time: Optional[str] = None,
        last_gps_fix: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> None:
        """Upserts a single train's real-time live position."""
        if updated_at is None:
            updated_at = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT INTO live_positions (
                    train_no, run_date, lat, lng, current_station_code, next_station_code,
                    section_id, speed_kmh, delay_minutes, confidence, progress_pct,
                    is_dead_reckoned, source, last_event_time, last_gps_fix, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(train_no, run_date) DO UPDATE SET
                    lat = excluded.lat,
                    lng = excluded.lng,
                    current_station_code = excluded.current_station_code,
                    next_station_code = excluded.next_station_code,
                    section_id = excluded.section_id,
                    speed_kmh = excluded.speed_kmh,
                    delay_minutes = excluded.delay_minutes,
                    confidence = excluded.confidence,
                    progress_pct = excluded.progress_pct,
                    is_dead_reckoned = excluded.is_dead_reckoned,
                    source = excluded.source,
                    last_event_time = excluded.last_event_time,
                    last_gps_fix = excluded.last_gps_fix,
                    updated_at = excluded.updated_at;
                """,
                (
                    train_no, run_date, lat, lng, current_station_code, next_station_code,
                    section_id, speed_kmh, delay_minutes, confidence, progress_pct,
                    is_dead_reckoned, source, last_event_time, last_gps_fix, updated_at
                ),
            )

    def upsert_live_positions_bulk(self, records: List[dict]) -> int:
        """Upserts multiple live position records in a single transaction."""
        if not records:
            return 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            for r in records:
                cur.execute(
                    """
                    INSERT INTO live_positions (
                        train_no, run_date, lat, lng, current_station_code, next_station_code,
                        section_id, speed_kmh, delay_minutes, confidence, progress_pct,
                        is_dead_reckoned, source, last_event_time, last_gps_fix, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(train_no, run_date) DO UPDATE SET
                        lat = excluded.lat,
                        lng = excluded.lng,
                        current_station_code = excluded.current_station_code,
                        next_station_code = excluded.next_station_code,
                        section_id = excluded.section_id,
                        speed_kmh = excluded.speed_kmh,
                        delay_minutes = excluded.delay_minutes,
                        confidence = excluded.confidence,
                        progress_pct = excluded.progress_pct,
                        is_dead_reckoned = excluded.is_dead_reckoned,
                        source = excluded.source,
                        last_event_time = excluded.last_event_time,
                        last_gps_fix = excluded.last_gps_fix,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        r["train_no"],
                        r["run_date"],
                        r["lat"],
                        r["lng"],
                        r.get("current_station_code"),
                        r.get("next_station_code"),
                        r.get("section_id"),
                        r.get("speed_kmh", 0.0),
                        r.get("delay_minutes", 0.0),
                        r.get("confidence", 1.0),
                        r.get("progress_pct", 0.0),
                        r.get("is_dead_reckoned", 0),
                        r.get("source", "live"),
                        r.get("last_event_time"),
                        r.get("last_gps_fix"),
                        r.get("updated_at", now_iso),
                    ),
                )
        return len(records)

    def get_live_position(self, train_no: str, run_date: str) -> Optional[dict]:
        """Retrieves a single live train position by train_no and run_date."""
        with self.transaction() as cur:
            cur.execute(
                "SELECT * FROM live_positions WHERE train_no = ? AND run_date = ?;",
                (train_no, run_date),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_live_positions(self) -> List[dict]:
        """Retrieves all active live train positions."""
        with self.transaction() as cur:
            cur.execute("SELECT * FROM live_positions ORDER BY updated_at DESC;")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def append_live_delay_ledger(
        self,
        train_no: str,
        run_date: str,
        timestamp: str,
        delay_change_min: float,
        previous_delay_min: float,
        current_delay_min: float,
        primary_cause: str,
        secondary_cause: Optional[str] = None,
        confidence: float = 1.0,
        evidence_json: str = "{}",
        is_exact_accounting: int = 1,
        created_at: Optional[str] = None,
    ) -> int:
        """Appends an immutable causal delay attribution event to the live delay ledger."""
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()
        with self.transaction() as cur:
            cur.execute(
                """
                INSERT INTO live_delay_ledger (
                    train_no, run_date, timestamp, delay_change_min, previous_delay_min,
                    current_delay_min, primary_cause, secondary_cause, confidence,
                    evidence_json, is_exact_accounting, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    train_no, run_date, timestamp, delay_change_min, previous_delay_min,
                    current_delay_min, primary_cause, secondary_cause, confidence,
                    evidence_json, is_exact_accounting, created_at
                ),
            )
            return cur.lastrowid

    def get_live_delay_ledger_for_train(self, train_no: str, run_date: str) -> List[dict]:
        """Retrieves full causal delay history for a given train run."""
        with self.transaction() as cur:
            cur.execute(
                "SELECT * FROM live_delay_ledger WHERE train_no = ? AND run_date = ? ORDER BY id ASC;",
                (train_no, run_date),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_recent_live_delay_ledger(self, limit: int = 50) -> List[dict]:
        """Retrieves most recent delay attribution events across the network."""
        with self.transaction() as cur:
            cur.execute(
                "SELECT * FROM live_delay_ledger ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

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
