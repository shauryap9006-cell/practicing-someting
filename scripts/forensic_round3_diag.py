"""Forensic Round 3 diagnostics — Finding 1 (route join) + Finding 2 (weather join)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import get_db
import pandas as pd

db = get_db()
print("=" * 70)
print("DIAGNOSTIC 1: route_stations coverage")
print("=" * 70)

with db.transaction() as cur:
    # How many events per month, and join-match rate
    cur.execute("""
        SELECT substr(se.run_date,1,7) AS month,
               COUNT(*) AS events,
               SUM(CASE WHEN rs.train_no IS NULL THEN 1 ELSE 0 END) AS unmatched
        FROM station_events se
        LEFT JOIN route_stations rs ON rs.train_no = se.train_no
        GROUP BY month ORDER BY month
    """)
    rows = cur.fetchall()

print(f"{'Month':<10} {'Events':>8} {'Unmatched':>10} {'Match%':>8}")
print("-" * 42)
for r in rows:
    pct = 100.0 * (r['events'] - r['unmatched']) / max(1, r['events'])
    print(f"{r['month']:<10} {r['events']:>8,} {r['unmatched']:>10,} {pct:>7.1f}%")

print("\n" + "=" * 70)
print("DIAGNOSTIC 2: train_no format mismatch for pre-2026-07 events")
print("=" * 70)

with db.transaction() as cur:
    cur.execute("""
        SELECT DISTINCT se.train_no FROM station_events se
        WHERE se.run_date < '2026-07-01'
          AND NOT EXISTS (
            SELECT 1 FROM route_stations rs WHERE rs.train_no = se.train_no
          )
        LIMIT 20
    """)
    missing = [r['train_no'] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT train_no FROM route_stations LIMIT 10")
    rs_sample = [r['train_no'] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT train_no FROM station_events WHERE run_date < '2026-07-01' LIMIT 10")
    se_old_sample = [r['train_no'] for r in cur.fetchall()]

print(f"Pre-2026-07 events with NO route_stations match (sample): {missing[:10]}")
print(f"route_stations train_no format (sample): {rs_sample[:5]}")
print(f"station_events old train_no format (sample): {se_old_sample[:5]}")

print("\n" + "=" * 70)
print("DIAGNOSTIC 3: route_stations schema — does it have a validity date column?")
print("=" * 70)

with db.transaction() as cur:
    cur.execute("PRAGMA table_info(route_stations)")
    cols = cur.fetchall()
    print("route_stations columns:")
    for c in cols:
        print(f"  {c['name']} ({c['type']})")

    # Check timetable_version or validity window columns
    col_names = [c['name'] for c in cols]
    if 'timetable_version' in col_names or 'valid_from' in col_names:
        if 'timetable_version' in col_names:
            cur.execute("SELECT timetable_version, COUNT(*) as cnt, MIN(run_date) as mn, MAX(run_date) as mx FROM route_stations GROUP BY timetable_version LIMIT 10")
        else:
            cur.execute("SELECT valid_from, COUNT(*) as cnt FROM route_stations GROUP BY valid_from LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            print(f"  {dict(r)}")
    else:
        print("  No timetable_version or valid_from column found")

print("\n" + "=" * 70)
print("DIAGNOSTIC 4: weather join for 2026 dates")
print("=" * 70)

with db.transaction() as cur:
    cur.execute("PRAGMA table_info(weather)")
    w_cols = [c['name'] for c in cur.fetchall()]
    print(f"weather columns: {w_cols}")

    cur.execute("SELECT MIN(date) as min_d, MAX(date) as max_d, COUNT(*) as cnt FROM weather")
    r = cur.fetchone()
    print(f"weather date range: {r['min_d']} -> {r['max_d']} ({r['cnt']:,} rows)")

    # Check null rate for fog features on 2026 events
    cur.execute("SELECT COUNT(*) as cnt FROM weather WHERE date >= '2026-01-01'")
    r2026 = cur.fetchone()
    print(f"weather rows with date >= 2026-01-01: {r2026['cnt']}")

    # Check what fog_flag looks like
    cur.execute("SELECT date, station_code, fog_flag FROM weather ORDER BY date DESC LIMIT 5")
    for r in cur.fetchall():
        print(f"  {dict(r)}")

print("\n" + "=" * 70)
print("DIAGNOSTIC 5: champion model — bidirectional GRU?")
print("=" * 70)

from ml.artifacts import get_champion_path
champ_path = None
try:
    champ_path = get_champion_path()
    print(f"Champion path: {champ_path}")
except Exception as e:
    print(f"get_champion_path() failed: {e}")

# Try loading directly
import torch
champ_candidates = list(Path("ml/artifacts").glob("*.pt")) + list(Path("ml/artifacts").glob("*.pkl"))
print(f"Champion checkpoint files: {[str(p) for p in champ_candidates]}")

for cp in champ_candidates:
    try:
        state = torch.load(cp, map_location="cpu", weights_only=True)
        if isinstance(state, dict):
            keys = list(state.keys())[:15]
            print(f"  {cp.name} state_dict keys (first 15): {keys}")
            # Bidirectional GRUs have 'reverse' or '_reverse' keys or double hidden_size
            bidi_keys = [k for k in state.keys() if 'reverse' in k.lower() or '_bw' in k.lower()]
            print(f"  Bidirectional indicator keys: {bidi_keys}")
    except Exception as e:
        print(f"  Failed to load {cp.name}: {e}")
