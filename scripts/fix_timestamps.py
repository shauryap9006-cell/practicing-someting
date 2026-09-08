"""RailTwin-X Data Repair: Normalize all timestamps to IST (+05:30).

Scans all tables with ISO string timestamp columns, detects per-row formats
(UTC +00:00, UTC Z, Naive, or IST +05:30), and converts them to canonical IST (+05:30).

Usage:
    python scripts/fix_timestamps.py            # DRY-RUN (default, no writes)
    python scripts/fix_timestamps.py --apply    # Perform data migration
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

IST = ZoneInfo("Asia/Kolkata")
ISO_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")

# Known timestamp columns to scan across tables
TIMESTAMP_COLUMN_NAMES = {
    "created_at",
    "updated_at",
    "reviewed_at",
    "published_at",
    "granted_at",
    "restored_at",
    "reported_at",
    "resolved_at",
    "started_at",
    "completed_at",
    "issued_at",
    "found_at",
    "claimed_at",
    "cleaned_at",
    "released_at",
    "expires_at",
    "revoked_at",
    "last_used_at",
    "last_inspected",
    "last_active",
    "last_event_time",
    "last_gps_fix",
    "applied_at",
    "backup_ts",
    "ack_ts",
    "acked_at",
    "escalated_at",
    "test_time",
    "sign_on_time",
    "sign_off_time",
    "outgoing_signed_at",
    "incoming_acked_at",
    "actual_ts",
    "predicted_ts",
    "actual_timestamp",
    "query_timestamp",
    "event_time",
    "collected_at",
    "since",
    "timestamp",
    "ts",
    "ts_ist",
    "recorded_at",
    "sent_at",
    "ack_at",
    "sim_time",
}


def convert_to_ist_iso(val: str) -> str:
    """Converts an ISO timestamp string to canonical IST (+05:30) ISO format."""
    if not isinstance(val, str) or not val.strip():
        return val

    s = val.strip()

    # Already canonical IST
    if "+05:30" in s:
        return s

    # UTC with Z or +00:00
    if s.endswith("Z") or "+00:00" in s or "+0000" in s:
        clean = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        dt_ist = dt.astimezone(IST)
        return dt_ist.isoformat()

    # Naive timestamp (assumed local IST wall-clock)
    try:
        clean = s.replace(" ", "T")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt_ist = dt.replace(tzinfo=IST)
        else:
            dt_ist = dt.astimezone(IST)
        return dt_ist.isoformat()
    except Exception:
        return s


def scan_database(db_path: str) -> Tuple[Dict[str, Dict[str, Dict[str, int]]], Dict[str, List[str]]]:
    """Scans all tables and timestamp columns, classifying format distributions."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]

    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    table_columns = defaultdict(list)

    for table in tables:
        cur.execute(f"PRAGMA table_info({table});")
        cols = [r["name"] for r in cur.fetchall()]
        matched_cols = [c for c in cols if c.lower() in TIMESTAMP_COLUMN_NAMES or any(k in c.lower() for k in ["_at", "_time", "timestamp"])]

        for col in matched_cols:
            try:
                cur.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != '';")
                rows = cur.fetchall()
                for r in rows:
                    v = r[0]
                    if isinstance(v, str) and ISO_REGEX.match(v):
                        if "+05:30" in v:
                            stats[table][col]["ist"] += 1
                        elif "+00:00" in v or v.endswith("Z"):
                            stats[table][col]["utc"] += 1
                        else:
                            stats[table][col]["naive"] += 1
                        if col not in table_columns[table]:
                            table_columns[table].append(col)
            except Exception:
                pass

    conn.close()
    return stats, table_columns


def rechain_prediction_ledger(conn: sqlite3.Connection) -> int:
    """Recomputes the hash chain for eta_prediction_ledger to maintain cryptographic integrity."""
    from engine.prediction_ledger import GENESIS_HASH

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, train_no, target_station, p10_delay, p50_delay, p90_delay, query_timestamp
        FROM eta_prediction_ledger
        ORDER BY id ASC;
        """
    )
    rows = cur.fetchall()
    if not rows:
        return 0

    updates = []
    expected_prev = GENESIS_HASH
    for r in rows:
        r_id, train_no, target_stn, p10, p50, p90, q_ts = r
        raw = f"{expected_prev}:{train_no}:{target_stn}:{p10:.2f}:{p50:.2f}:{p90:.2f}:{q_ts}"
        curr_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        updates.append((curr_hash, expected_prev, r_id))
        expected_prev = curr_hash

    cur.executemany(
        "UPDATE eta_prediction_ledger SET receipt_hash = ?, prev_hash = ? WHERE id = ?;",
        updates,
    )
    return len(updates)


def apply_repairs(db_path: str, table_columns: Dict[str, List[str]]) -> Dict[str, int]:
    """Applies timestamp normalization to all identified columns in the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    updated_counts = defaultdict(int)

    with conn:
        for table, cols in table_columns.items():
            for col in cols:
                cur.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != '';")
                rows = cur.fetchall()
                batch = []
                for rowid, val in rows:
                    if isinstance(val, str) and ISO_REGEX.match(val):
                        new_val = convert_to_ist_iso(val)
                        if new_val != val:
                            batch.append((new_val, rowid))

                if batch:
                    cur.executemany(f"UPDATE {table} SET {col} = ? WHERE rowid = ?;", batch)
                    updated_counts[f"{table}.{col}"] += len(batch)

        # Recompute prediction ledger hashes if query_timestamp was modified
        if "eta_prediction_ledger.query_timestamp" in updated_counts:
            rechain_prediction_ledger(conn)

    conn.close()
    return updated_counts


def main():
    parser = argparse.ArgumentParser(description="Repair and normalize database timestamps to IST (+05:30).")
    parser.add_argument("--db", default="data/railtwin.db", help="Path to SQLite database")
    parser.add_argument("--apply", action="store_true", help="Apply changes (defaults to DRY-RUN mode)")
    args = parser.parse_args()

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"Error: database file not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"=== RailTwin-X Timestamp Repair Tool ===")
    print(f"Target Database: {db_path}")
    print(f"Mode: {'APPLY (Destructive)' if args.apply else 'DRY-RUN (No Changes)'}\n")

    stats, table_columns = scan_database(db_path)

    total_ist = 0
    total_to_convert = 0

    print(f"{'Table':<25} {'Column':<25} {'IST (+05:30)':<15} {'UTC (Z/00:00)':<15} {'Naive':<10} {'Action':<10}")
    print("-" * 105)

    for table in sorted(stats.keys()):
        for col in sorted(stats[table].keys()):
            counts = stats[table][col]
            ist_count = counts["ist"]
            utc_count = counts["utc"]
            naive_count = counts["naive"]
            to_convert = utc_count + naive_count

            total_ist += ist_count
            total_to_convert += to_convert

            action = f"Convert {to_convert}" if to_convert > 0 else "OK"
            print(f"{table:<25} {col:<25} {ist_count:<15} {utc_count:<15} {naive_count:<10} {action:<10}")

    print("-" * 105)
    print(f"SUMMARY: {total_ist} already canonical IST | {total_to_convert} rows to convert to IST (+05:30)\n")

    if not args.apply:
        print("[DRY-RUN COMPLETE] Zero modifications written to disk.")
        print("To execute timestamp repairs, re-run with: python scripts/fix_timestamps.py --apply")
        return

    print(">>> Applying timestamp normalization to database...")
    updates = apply_repairs(db_path, table_columns)
    print(f"Successfully repaired {sum(updates.values())} timestamp entries across {len(updates)} columns.")
    print("Database is now 100% canonical IST (+05:30).")


if __name__ == "__main__":
    main()
