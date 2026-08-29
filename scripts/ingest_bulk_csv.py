"""RailTwin-X Bulk CSV/JSON Ingestion Engine.

Ingests static or exported datasets from Kaggle, Data.gov.in, NTES, or scraper dumps
directly into the RailTwin-X SQLite database with schema mapping and quality gates.

Usage:
    python scripts/ingest_bulk_csv.py path/to/file.csv [--source generic|kaggle|ntes]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Set
import pandas as pd

# Ensure root directory is on PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings
from data.db import Database, get_db
from collector.quality import QualityGate

COLUMN_ALIASES = {
    "train_no": ["train_no", "train_number", "trainno", "train_num", "train", "Train Number", "Train No", "TRAIN_NO"],
    "station_code": ["station_code", "stn_code", "station", "stn", "station_cd", "Station Code", "Station", "STATION_CODE"],
    "run_date": ["run_date", "date", "journey_date", "start_date", "Date", "RUN_DATE", "Journey Date"],
    "seq": ["seq", "sequence", "stop_number", "stop_seq", "Seq", "SEQ", "Stop Number"],
    "sched_arr": ["sched_arr", "sch_arr", "scheduled_arrival", "sched_arrival", "Schedule Arrival", "SCHED_ARR", "Arr Time"],
    "actual_arr": ["actual_arr", "act_arr", "actual_arrival", "Actual Arrival", "ACTUAL_ARR", "Actual Arr"],
    "sched_dep": ["sched_dep", "sch_dep", "scheduled_departure", "sched_departure", "Schedule Departure", "SCHED_DEP", "Dep Time"],
    "actual_dep": ["actual_dep", "act_dep", "actual_departure", "Actual Departure", "ACTUAL_DEP", "Actual Dep"],
    "delay_arr_min": ["delay_arr_min", "delay_arr", "arrival_delay", "delay_arrival", "Delay Arrival", "Arr Delay", "arr_delay_m"],
    "delay_dep_min": ["delay_dep_min", "delay_dep", "departure_delay", "delay_departure", "Delay Departure", "Dep Delay", "dep_delay_m"],
}

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Maps varying external column headers into canonical RailTwin-X schema names."""
    rename_map = {}
    lower_cols = {str(c).strip().lower(): c for c in df.columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            a_lower = alias.lower()
            if a_lower in lower_cols:
                rename_map[lower_cols[a_lower]] = canonical
                break
    return df.rename(columns=rename_map)

def parse_time_to_hhmm(val: Optional[str]) -> Optional[str]:
    """Parses arbitrary time string into HH:MM."""
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str in ("--", "None", "nan", "null"):
        return None
    if ":" in val_str:
        parts = val_str.split(":")
        if len(parts) >= 2:
            try:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            except Exception:
                pass
    return val_str[:5]

def ingest_bulk_dataset(
    file_path: str | Path,
    db: Optional[Database] = None,
    source_tag: str = "bulk_csv",
) -> dict:
    """Ingests a CSV or JSON dataset into the station_events table."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    print(f"[INFO] Reading dataset from {path}...")
    if path.suffix.lower() == ".json":
        df = pd.read_json(path)
    else:
        df = pd.read_csv(path, low_memory=False)

    df = normalize_dataframe_columns(df)
    target_db = db or get_db()

    for req in ["train_no", "station_code"]:
        if req not in df.columns:
            raise ValueError(f"Dataset missing critical column: {req}. Available columns: {list(df.columns)}")

    df["train_no"] = df["train_no"].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["station_code"] = df["station_code"].astype(str).str.strip().str.upper()

    if "run_date" in df.columns:
        df["run_date"] = pd.to_datetime(df["run_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        df["run_date"] = datetime.date.today().strftime("%Y-%m-%d")

    if "seq" not in df.columns:
        df["seq"] = df.groupby(["train_no", "run_date"]).cumcount() + 1
    else:
        df["seq"] = pd.to_numeric(df["seq"], errors="coerce").fillna(1).astype(int)

    if "sched_arr" in df.columns:
        df["sched_arr"] = df["sched_arr"].apply(parse_time_to_hhmm)
    else:
        df["sched_arr"] = None

    if "actual_arr" in df.columns:
        df["actual_arr"] = df["actual_arr"].apply(parse_time_to_hhmm)
    else:
        df["actual_arr"] = df["sched_arr"]

    if "sched_dep" in df.columns:
        df["sched_dep"] = df["sched_dep"].apply(parse_time_to_hhmm)
    else:
        df["sched_dep"] = None

    if "actual_dep" in df.columns:
        df["actual_dep"] = df["actual_dep"].apply(parse_time_to_hhmm)
    else:
        df["actual_dep"] = df["sched_dep"]

    if "delay_arr_min" not in df.columns:
        df["delay_arr_min"] = 0
    else:
        df["delay_arr_min"] = pd.to_numeric(df["delay_arr_min"], errors="coerce").fillna(0).astype(int)

    if "delay_dep_min" not in df.columns:
        df["delay_dep_min"] = df["delay_arr_min"]
    else:
        df["delay_dep_min"] = pd.to_numeric(df["delay_dep_min"], errors="coerce").fillna(df["delay_arr_min"]).astype(int)

    collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with target_db.transaction() as cur:
        cur.execute("SELECT code FROM stations")
        existing_stations = {r["code"] for r in cur.fetchall()}

        cur.execute("SELECT train_no FROM trains")
        existing_trains = {r["train_no"] for r in cur.fetchall()}

        missing_stations = set(df["station_code"]) - existing_stations
        for stn in missing_stations:
            cur.execute(
                "INSERT OR IGNORE INTO stations (code, name, lat, lon, zone, category, is_junction, platforms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (stn, f"Station {stn}", 26.8, 80.3, "NR", "NSG-2", 0, 2)
            )

        missing_trains = set(df["train_no"]) - existing_trains
        for tr in missing_trains:
            cur.execute(
                "INSERT OR IGNORE INTO trains (train_no, name, class, priority) VALUES (?, ?, ?, ?)",
                (tr, f"Train {tr}", "superfast", 2)
            )

    rows_to_insert = []
    quarantined = 0
    for row in df.itertuples(index=False):
        d_arr = getattr(row, "delay_arr_min", 0)
        d_dep = getattr(row, "delay_dep_min", d_arr)

        if d_arr > settings.MAX_SANITY_DELAY_MINUTES or d_arr < settings.MIN_SANITY_DELAY_MINUTES:
            quarantined += 1
            continue

        rows_to_insert.append((
            str(row.train_no),
            str(row.run_date),
            int(row.seq),
            str(row.station_code),
            getattr(row, "sched_arr", None),
            getattr(row, "actual_arr", None),
            getattr(row, "sched_dep", None),
            getattr(row, "actual_dep", None),
            int(d_arr),
            int(d_dep),
            collected_at
        ))

    with target_db.transaction() as cur:
        cur.executemany(
            """
            INSERT OR REPLACE INTO station_events (
                train_no, run_date, seq, station_code, sched_arr, actual_arr, sched_dep, actual_dep,
                delay_arr_min, delay_dep_min, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert
        )

    print(f"[SUCCESS] Ingested {len(rows_to_insert):,} rows into station_events ({quarantined:,} quarantined).")
    return {
        "total_rows_read": len(df),
        "rows_ingested": len(rows_to_insert),
        "rows_quarantined": quarantined,
        "unique_trains": int(df["train_no"].nunique()),
        "unique_dates": int(df["run_date"].nunique()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest bulk railway CSV/JSON dataset into RailTwin-X SQLite DB.")
    parser.add_argument("file_path", type=str, help="Path to CSV or JSON data file")
    parser.add_argument("--source", type=str, default="bulk_csv", help="Source name tag")
    args = parser.parse_args()
    summary = ingest_bulk_dataset(args.file_path, source_tag=args.source)
    print("=== Ingestion Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
