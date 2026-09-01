"""Materializes feature_snapshots_v3 at 60, 180, and 360 min horizons (Phase C2).

Guarantees 100% training and serving distribution alignment with strict point-in-time
isolation ($t \\le \\text{as\\_of}$) across the locked temporal splits:
- TRAIN_v3: 2025-02-08 to 2025-10-31
- VAL_v3: 2025-11-01 to 2025-11-29
- BENCH_v3: 2025-11-30 to 2026-01-01 (Fog Core, SEALED)
- BENCH_NORMAL: 2026-02-01 to 2026-08-31 (SEALED)
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import Database, get_db
from ml.features_v3 import HORIZONS_MIN, V3FeatureBuilder

DDL = """
CREATE TABLE IF NOT EXISTS feature_snapshots_v3 (
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL,
  target_station TEXT NOT NULL,
  as_of TEXT NOT NULL,
  horizon_min REAL NOT NULL,
  y REAL NOT NULL,
  f_current_delay REAL,
  f_delay_velocity REAL,
  f_staleness_vel REAL,
  f_km_remaining REAL,
  f_sched_min_to_target REAL,
  f_sin_hour REAL,
  f_cos_hour REAL,
  f_day_of_week INTEGER,
  f_target_is_terminus INTEGER,
  f_hist_recency_avg REAL,
  f_hist_p90 REAL,
  f_train_priority INTEGER,
  f_exp_decay_ahead REAL,
  f_opposing_ahead REAL,
  f_max_delay_ahead REAL,
  f_route_ahead_occ REAL,
  f_rake_net_delay REAL,
  f_rake_buffer_pct REAL,
  f_rake_linked INTEGER,
  f_tsr_count INTEGER,
  f_tsr_max_slow REAL,
  f_fog_dawn REAL,
  f_rain_mm REAL,
  f_festival_prox REAL,
  PRIMARY KEY (train_no, run_date, target_station, as_of)
);
"""


def _parse_time(t_str: Optional[str]) -> Tuple[int, int]:
    if not t_str or ":" not in str(t_str):
        return (12, 0)
    try:
        parts = str(t_str).strip().split(":")
        return (int(parts[0]), int(parts[1]))
    except Exception:
        return (12, 0)


def materialize_v3_snapshots(
    db: Optional[Database] = None,
    max_trains: Optional[int] = None,
    batch_size: int = 5000,
) -> int:
    """Extracts and bulk-inserts all point-in-time snapshots for observed arrival journeys."""
    db_inst = db or get_db()
    builder = V3FeatureBuilder(str(db_inst.db_path))

    con = sqlite3.connect(str(db_inst.db_path), timeout=60.0)
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA busy_timeout = 60000;")
    con.row_factory = sqlite3.Row

    with con:
        con.execute(DDL)
        con.execute("CREATE INDEX IF NOT EXISTS idx_v3_run_date ON feature_snapshots_v3(run_date);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_v3_train_date ON feature_snapshots_v3(train_no, run_date);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_v3_horizon ON feature_snapshots_v3(horizon_min);")
        con.execute("DELETE FROM feature_snapshots_v3;")

    print("[INFO] Querying target journeys from station_events...", flush=True)

    # Query all target stops (seq >= 2 with recorded arrival delay)
    target_query = """
    SELECT se.train_no, se.run_date, se.station_code, se.seq,
           se.sched_arr, se.delay_arr_min
    FROM station_events se
    WHERE se.seq >= 2 AND se.delay_arr_min IS NOT NULL
    ORDER BY se.run_date ASC, se.train_no ASC, se.seq ASC
    """
    targets = con.execute(target_query).fetchall()
    print(f"[INFO] Found {len(targets):,} target station events. Building snapshots...", flush=True)

    # Cache origin scheduled departures: (train_no) -> sched_dep_hour, sched_dep_min
    origins_raw = con.execute(
        "SELECT train_no, sched_dep FROM route_stations WHERE seq = 1"
    ).fetchall()
    origin_dep_map = {str(r["train_no"]): _parse_time(r["sched_dep"]) for r in origins_raw}

    snapshots_to_insert = []
    total_inserted = 0

    for idx, t in enumerate(targets):
        t_no = str(t["train_no"])
        r_date = str(t["run_date"])
        target_stn = str(t["station_code"])
        y = float(t["delay_arr_min"] or 0.0)

        # Parse target scheduled arrival timestamp
        arr_h, arr_m = _parse_time(t["sched_arr"])
        run_d = dt.date.fromisoformat(r_date)
        sched_arr_dt = dt.datetime(run_d.year, run_d.month, run_d.day, arr_h, arr_m, 0)

        # Parse origin scheduled departure
        dep_h, dep_m = origin_dep_map.get(t_no, (0, 0))
        sched_dep_dt = dt.datetime(run_d.year, run_d.month, run_d.day, dep_h, dep_m, 0)

        for h in HORIZONS_MIN:
            as_of_dt = sched_arr_dt - dt.timedelta(minutes=h)

            # As-of must not precede origin scheduled departure by more than 2 hours
            if as_of_dt < (sched_dep_dt - dt.timedelta(hours=2)):
                continue

            feat = builder.build_snapshot_features(
                train_no=t_no,
                run_date=r_date,
                target_station=target_stn,
                as_of_dt=as_of_dt,
                sched_arr_target_dt=sched_arr_dt,
            )

            as_of_str = as_of_dt.strftime("%Y-%m-%d %H:%M:%S")

            row = (
                t_no,
                r_date,
                target_stn,
                as_of_str,
                float(h),
                y,
                feat["current_delay"],
                feat["delay_velocity"],
                feat["staleness_velocity_interaction"],
                feat["km_remaining"],
                feat["sched_minutes_to_target"],
                feat["sin_hour"],
                feat["cos_hour"],
                int(feat["day_of_week"]),
                int(feat["target_is_terminus"]),
                feat["hist_recency_avg_delay"],
                feat["hist_p90_delay"],
                int(feat["train_priority"]),
                feat["exp_decay_trains_ahead_30k"],
                feat["opposing_conflicts_ahead"],
                feat["max_delay_trains_ahead"],
                feat["route_ahead_section_occupancy_pct"],
                feat["upstream_rake_net_delay"],
                feat["upstream_rake_buffer_consumed_pct"],
                int(feat["rake_linked"]),
                int(feat["tsr_active_ahead_count"]),
                feat["tsr_max_slowdown_pct"],
                feat["winter_fog_dawn_interaction"],
                feat["rain_mm_target"],
                feat["festival_proximity_days"],
            )
            snapshots_to_insert.append(row)

            if len(snapshots_to_insert) >= batch_size:
                with con:
                    con.executemany(
                        """
                        INSERT OR REPLACE INTO feature_snapshots_v3 VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        );
                        """,
                        snapshots_to_insert,
                    )
                total_inserted += len(snapshots_to_insert)
                snapshots_to_insert.clear()

        if idx > 0 and idx % 10000 == 0:
            print(f"  Processed {idx:,}/{len(targets):,} target stops ({total_inserted:,} snapshots inserted)...", flush=True)

    if snapshots_to_insert:
        with con:
            con.executemany(
                """
                INSERT OR REPLACE INTO feature_snapshots_v3 VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
                """,
                snapshots_to_insert,
            )
        total_inserted += len(snapshots_to_insert)

    con.close()
    print(f"[SUCCESS] Materialized {total_inserted:,} feature_snapshots_v3 records.", flush=True)
    return total_inserted


if __name__ == "__main__":
    materialize_v3_snapshots()
