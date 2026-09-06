# -*- coding: utf-8 -*-
"""Route-join root cause: which hypothesis explains the 17.5-month gap?"""
import sqlite3, gzip, shutil, re
from pathlib import Path

db_path = "data/railtwin.db"
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
def cols(t): return [r["name"] for r in con.execute(f"PRAGMA table_info({t})")]

print("route_stations columns:", cols("route_stations"))

# Hypothesis A: route table truncated / timetable-version bounded
print("\n[Hypothesis A] Timetable version / Date bounds in route_stations:")
for c in ("timetable_version", "version", "ttv", "run_date", "valid_from", "start_date"):
    if c in cols("route_stations"):
        print(f"  route_stations column {c}: {con.execute(f'SELECT DISTINCT {c} FROM route_stations').fetchall()}")

# Hypothesis B: Train-number format drift / Unmatched train numbers
print("\n[Hypothesis B] Sample unmatched train numbers pre-2025-07:")
try:
    unmatched_pre = con.execute("""SELECT DISTINCT se.train_no FROM station_events se
        WHERE se.run_date < '2025-07-01' AND NOT EXISTS
        (SELECT 1 FROM route_stations rs WHERE rs.train_no = se.train_no) LIMIT 15""").fetchall()
    print(f"  unmatched pre-2025-07 count in sample: {len(unmatched_pre)}")
    for r in unmatched_pre:
        print(f"    unmatched: '{r[0]}'")
except Exception as e:
    print(f"  query failed: {e}")

# Degradation curve: monthly match rate of station_events JOIN route_stations
print("\nMonthly route-join match rate (events vs route_stations):")
for r in con.execute("""SELECT substr(se.run_date,1,7) mon, COUNT(*) events,
    SUM(CASE WHEN rs.train_no IS NULL THEN 1 ELSE 0 END) unmatched
    FROM station_events se LEFT JOIN route_stations rs ON (rs.train_no = se.train_no AND rs.seq = se.seq)
    GROUP BY mon ORDER BY mon"""):
    unmatched_count = r["unmatched"] or 0
    pct_unmatched = 100 * unmatched_count / max(r["events"], 1)
    pct_matched = 100.0 - pct_unmatched
    print(f"  {r['mon']}: {r['events']:>9,} events | matched={pct_matched:6.2f}% | unmatched={pct_unmatched:6.2f}% ({unmatched_count:>7,})")

# Print the exact ON clause in both paths -- are training and serving using the SAME join?
print("\n" + "="*72)
print("ROUTE JOIN CODE PATH SCAN")
print("="*72)
for f in ("ml/train_v2.py", "ml/snapshots.py", "ml/seq_dataset.py", "api/predictor.py"):
    p = Path(f)
    if p.exists():
        src = p.read_text(encoding="utf-8", errors="replace")
        hits = [l.strip() for l in src.splitlines()
                if re.search(r"\bJOIN\b|\bjoin\b.*route", l, re.IGNORECASE)]
        print(f"\n{f}:")
        for h in hits[:5]:
            print(f"  {h}")
con.close()
