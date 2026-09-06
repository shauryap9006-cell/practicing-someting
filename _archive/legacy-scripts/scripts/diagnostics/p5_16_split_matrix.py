# -*- coding: utf-8 -*-
"""Journey-granularity overlap matrix + fog-allocation options for v3 splits."""
import sqlite3, gzip, shutil, json, sys, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from data.db import Database, get_db
from ml.train_v2 import get_full_corpus_splits

db_path = "data/railtwin.db"
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row

print("="*72)
print("1. CURRENT V2 SPLIT WINDOWS & JOURNEY OVERLAP MATRIX")
print("="*72)
db_inst = get_db()
v2_splits = get_full_corpus_splits(db_inst)

split_journeys = {}
for name, dates in [
    ("TRAIN_v2", v2_splits["train_dates"]),
    ("VAL_v2",   v2_splits["val_dates"]),
    ("BENCH_v2", v2_splits["bench_fog_dates"]),
]:
    sql = "SELECT DISTINCT train_no, run_date FROM station_events WHERE run_date IN (%s)" % ",".join("?"*len(dates))
    journeys = set(con.execute(sql, tuple(dates)).fetchall())
    split_journeys[name] = journeys
    print(f"  {name:10s} dates={len(dates):>3} | distinct journeys (train_no, run_date)={len(journeys):>6,}")

# Overlap Matrix
print("\nJourney-Granularity Overlap Matrix (Intersection count must be 0):")
keys = list(split_journeys.keys())
for i, a in enumerate(keys):
    for b in keys[i+1:]:
        ov = split_journeys[a] & split_journeys[b]
        status = "*** DATA LEAK DETECTED ***" if ov else "PASS (0 overlap)"
        print(f"  {a:10s} intersect {b:10s} = {len(ov):>4} journeys -> {status}")

print("\n" + "="*72)
print("2. FOG INVENTORY ALLOCATION OPTIONS FOR SPLITS V3")
print("="*72)
inv_path = Path("control-room/23_DIAGNOSTICS/fog_inventory.json")
assert inv_path.exists(), "fog_inventory.json missing - run Phase 3 first"
fog_all = set(json.loads(inv_path.read_text(encoding="utf-8")))

corpus_dates = [r[0] for r in con.execute("SELECT DISTINCT run_date FROM station_events ORDER BY run_date")]
corpus_fog = sorted(fog_all & set(corpus_dates))
print(f"Total fog dates with events in corpus: {len(corpus_fog)}")

fog_by_period = {
    "Feb 2025 Fog Tail (2025-02-08..2025-02-28)": [d for d in corpus_fog if d.startswith("2025-02")],
    "Nov 2025 Shoulder Fog (2025-11-01..2025-11-30)": [d for d in corpus_fog if d.startswith("2025-11")],
    "Dec 2025 - Jan 2026 Winter Core (Peak Fog)": [d for d in corpus_fog if d.startswith("2025-12") or d.startswith("2026-01")],
    "Feb 2026 Fog Tail (2026-02-01..2026-02-28)": [d for d in corpus_fog if d.startswith("2026-02")],
    "Aug 2026 Monsoon Slices (Rain Fog)": [d for d in corpus_fog if d.startswith("2026-08")],
}

for period, p_dates in fog_by_period.items():
    ev_cnt = 0
    if p_dates:
        sql = "SELECT COUNT(*) FROM station_events WHERE run_date IN (%s)" % ",".join("?"*len(p_dates))
        ev_cnt = con.execute(sql, tuple(p_dates)).fetchone()[0]
    print(f"  {period:<48s}: {len(p_dates):>2} days | {ev_cnt:>6,} station events")

print("\n" + "="*72)
print("3. PROPOSED V3 SPLIT DESIGN (True Temporal + Winter Fog Balanced)")
print("="*72)
# Option A: Feb 2025 Fog in Train, Dec 2025 - Jan 2026 Core Winter Fog in Benchmark
train_v3_dates = [d for d in corpus_dates if d < "2025-11-01"]
val_v3_dates   = [d for d in corpus_dates if "2025-11-01" <= d < "2025-12-01"]
bench_winter_core = [d for d in corpus_fog if d.startswith("2025-12") or d.startswith("2026-01")]

bench_v3_dates = set()
for d in bench_winter_core:
    dt = datetime.date.fromisoformat(d)
    for off in (-1, 0, 1):
        b_str = (dt + datetime.timedelta(days=off)).isoformat()
        if b_str in corpus_dates:
            bench_v3_dates.add(b_str)
bench_v3_dates = sorted(bench_v3_dates)

# Clean train and val from benchmark overlap
train_v3_dates = [d for d in train_v3_dates if d not in bench_v3_dates]
val_v3_dates = [d for d in val_v3_dates if d not in bench_v3_dates]

sql_t = "SELECT COUNT(*) FROM station_events WHERE run_date IN (%s)" % ",".join("?"*len(train_v3_dates))
sql_v = "SELECT COUNT(*) FROM station_events WHERE run_date IN (%s)" % ",".join("?"*len(val_v3_dates))
sql_b = "SELECT COUNT(*) FROM station_events WHERE run_date IN (%s)" % ",".join("?"*len(bench_v3_dates))

n_t = con.execute(sql_t, tuple(train_v3_dates)).fetchone()[0]
n_v = con.execute(sql_v, tuple(val_v3_dates)).fetchone()[0]
n_b = con.execute(sql_b, tuple(bench_v3_dates)).fetchone()[0]

print("V3 Proposed Allocation:")
print(f"  TRAIN_v3 : {min(train_v3_dates)} to {max(train_v3_dates)} ({len(train_v3_dates)} days) | {n_t:>7,} events | Contains Feb 2025 real fog tail (11k events)")
print(f"  VAL_v3   : {min(val_v3_dates)} to {max(val_v3_dates)} ({len(val_v3_dates)} days) | {n_v:>7,} events | Contiguous pre-winter validation")
print(f"  BENCH_v3 : {min(bench_v3_dates)} to {max(bench_v3_dates)} ({len(bench_v3_dates)} days) | {n_b:>7,} events | Pure Dec 2025 - Jan 2026 Core Winter Fog")

set_t = set(train_v3_dates)
set_v = set(val_v3_dates)
set_b = set(bench_v3_dates)
print(f"\nV3 Date Overlaps: Train intersect Val = {len(set_t & set_v)}, Train intersect Bench = {len(set_t & set_b)}, Val intersect Bench = {len(set_v & set_b)}")

con.close()
