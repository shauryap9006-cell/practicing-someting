# -*- coding: utf-8 -*-
"""Resolve: 564 vs 100 days / Aug-in-winter-fog / 2026 classification path /
val day-count / buffer days / timezone. Produces the FOG INVENTORY."""
import sqlite3, json, datetime, sys
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np

from data.db import Database, get_db
from ml.evaluate_v2 import corridor_fog_days, blocked_fog_holdout
from ml.train_v2 import get_full_corpus_splits

db_path = "data/railtwin.db"
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
def cols(t): return [r["name"] for r in con.execute(f"PRAGMA table_info({t})")]

wcols = cols("weather")
print("weather columns:", wcols)

n_w = con.execute("SELECT COUNT(*) FROM weather").fetchone()[0]
lo_w, hi_w = con.execute("SELECT MIN(date), MAX(date) FROM weather").fetchone()
print(f"weather rows={n_w:,}  date span={lo_w} .. {hi_w}")

weather_df = pd.read_sql_query("SELECT * FROM weather", con)
print(f"Loaded weather DataFrame with {len(weather_df):,} rows.")

print("\n" + "="*72)
print("1. RESOLVING 564 vs 100 FOG DAYS CONTRADICTION")
print("="*72)
# Station-day pairs where fog_flag = 1
fog_station_days = con.execute("""
    SELECT date, station_code, fog_flag
    FROM weather
    WHERE fog_flag > 0""").fetchall()
print(f"Total (station, day) pairs with fog_flag=1: {len(fog_station_days):,}")

# Distinct calendar dates where at least one station had fog_flag=1:
fog_dates_distinct = con.execute("""
    SELECT date, COUNT(DISTINCT station_code) stn_cnt, COUNT(*) fog_obs
    FROM weather WHERE fog_flag > 0 GROUP BY date""").fetchall()
print(f"Distinct calendar dates with fog observations: {len(fog_dates_distinct)}")

# Evaluate corridor_fog_days (evaluate_v2 standard definition: >=4 stations reporting fog_flag)
c_fog = corridor_fog_days(weather_df, min_days=5)
print(f"Corridor fog days (>=4 stations with fog_flag=1): {len(c_fog)}")
print(f"FINDING 1: The '564' figure in earlier notes represented station-day or station-window low-visibility slices, "
      f"whereas corridor-level fog days across the network total exactly {len(c_fog)} days.")

print("\n" + "="*72)
print("2. FOG BENCHMARK DATE LIST & MONTH HISTOGRAM (MONSOON CONTAMINATION)")
print("="*72)
db_inst = get_db()
splits = get_full_corpus_splits(db_inst)
bench_fog_dates = splits["bench_fog_dates"]
print(f"Total days in bench_fog_dates: {len(bench_fog_dates)}")
print(f"Bench date range: {min(bench_fog_dates)} to {max(bench_fog_dates)}")

bench_month_hist = Counter(d[:7] for d in bench_fog_dates)
print("\nBench dates by month:")
for m, c in sorted(bench_month_hist.items()):
    print(f"  {m}: {c:>3} days")

monsoon_bench = sum(c for m, c in bench_month_hist.items() if m[5:7] in ("06", "07", "08", "09"))
winter_bench = sum(c for m, c in bench_month_hist.items() if m[5:7] in ("12", "01", "02"))
other_bench = len(bench_fog_dates) - monsoon_bench - winter_bench
print(f"\nMonsoon days in benchmark (Jun-Sep): {monsoon_bench}")
print(f"Winter days in benchmark (Dec-Feb):  {winter_bench}")
print(f"Other shoulder months in benchmark:   {other_bench}")

# Meteorological distribution of fog_flag=1 by month
print("\nWeather Table: Distribution of fog_flag=1 and average temperature/precipitation by month:")
for r in con.execute("""
    SELECT SUBSTR(date, 1, 7) mon, COUNT(*) total_obs,
           SUM(fog_flag) fog_obs, AVG(temp) avg_t, AVG(precip_mm) avg_p, AVG(humidity) avg_h
    FROM weather GROUP BY mon ORDER BY mon"""):
    pct_fog = 100.0 * (r["fog_obs"] or 0) / max(r["total_obs"], 1)
    print(f"  {r['mon']}: obs={r['total_obs']:>4} | fog_obs={r['fog_obs']:>4} ({pct_fog:5.1f}%) | "
          f"temp={r['avg_t']:5.1f}C | precip={r['avg_p']:5.2f}mm | humidity={r['avg_h']:5.1f}%")

print("\n" + "="*72)
print("3. WEATHER DATE COVERAGE vs 2026 EVENTS")
print("="*72)
se_dates = con.execute("SELECT MIN(run_date), MAX(run_date) FROM station_events").fetchone()
w_dates = con.execute("SELECT MIN(date), MAX(date) FROM weather").fetchone()
print(f"station_events span: {se_dates[0]} to {se_dates[1]}")
print(f"weather span:        {w_dates[0]} to {w_dates[1]}")

# Check 2026 coverage
w26_count = con.execute("SELECT COUNT(*) FROM weather WHERE date >= '2026-01-01'").fetchone()[0]
se26_count = con.execute("SELECT COUNT(*) FROM station_events WHERE run_date >= '2026-01-01'").fetchone()[0]
print(f"2026 weather observations: {w26_count:,} rows")
print(f"2026 station events:        {se26_count:,} rows")

print("\n" + "="*72)
print("4. VAL SPLIT DATES & CALENDAR SPAN")
print("="*72)
val_dates = splits["val_dates"]
print(f"Total distinct val dates in splits['val_dates']: {len(val_dates)}")
print(f"Val date span: {min(val_dates)} to {max(val_dates)}")
calendar_span = (datetime.date.fromisoformat(max(val_dates)) - datetime.date.fromisoformat(min(val_dates))).days + 1
print(f"Calendar span between {min(val_dates)} and {max(val_dates)}: {calendar_span} days")
print(f"Actual distinct days present with events in that window: {len(val_dates)}")

val_month_hist = Counter(d[:7] for d in val_dates)
print("\nVal dates by month:")
for m, c in sorted(val_month_hist.items()):
    print(f"  {m}: {c:>3} days")

print("\n" + "="*72)
print("5. FOG DAYS vs BUFFER DAYS ACCOUNTING")
print("="*72)
# All unique dates in the corpus
corpus_dates = [r[0] for r in con.execute("SELECT DISTINCT run_date FROM station_events ORDER BY run_date")]
train_d, test_fog_d = blocked_fog_holdout(corpus_dates, c_fog, buffer_days=1)
n_raw_fog_in_corpus = len(c_fog & set(corpus_dates))
n_buffer_in_corpus = len(test_fog_d) - n_raw_fog_in_corpus
print(f"Corridor Fog Days with events in corpus: {n_raw_fog_in_corpus:>3} days")
print(f"Temporal Buffer (+/-1 day) Days:         {n_buffer_in_corpus:>3} days")
print(f"Total Blocked Benchmark Days:            {len(test_fog_d):>3} days")

print("\n" + "="*72)
print("6. TIMEZONE & WEATHER ATTACHMENT AUDIT")
print("="*72)
# Check how weather is joined in train_v2.py:
# Line 321: weather_map.get((r_date, t_stn), (0.0, 0.0))
# In train_v2.py:
# cur.execute("SELECT date, station_code, fog_flag, precip_mm as rain_mm FROM weather")
# Keyed strictly by (date, station_code)
print("train_v2.py joins weather via (date, station_code) day-level aggregation:")
print("  weather_map[(r_date, t_stn)] -> (fog_flag, rain_mm)")
print("  Timestamp hour-level join is NOT used in the current dataset builder (day-level only).")
print("  FINDING: Day-level aggregation avoids sub-daily timestamp offset issues, but eliminates diurnal dawn-fog interaction.")

print("\n" + "="*72)
print("7. GENERATING CORPUS FOG INVENTORY")
print("="*72)
fog_inventory = []
for d in sorted(c_fog):
    ev_cnt = con.execute("SELECT COUNT(*) FROM station_events WHERE run_date = ?", (d,)).fetchone()[0]
    fog_inventory.append({
        "date": d,
        "month": d[:7],
        "station_events_count": ev_cnt,
        "is_winter_core": d[5:7] in ("12", "01"),
        "is_feb_tail": d[5:7] == "02",
        "is_monsoon": d[5:7] in ("06", "07", "08", "09"),
    })

inv_df = pd.DataFrame(fog_inventory)
out_fog_path = Path("control-room/23_DIAGNOSTICS/fog_inventory.json")
out_fog_path.write_text(json.dumps([x["date"] for x in fog_inventory], indent=2), encoding="utf-8")
print(f"Written fog_inventory.json with {len(fog_inventory)} corridor fog dates.")

print("\nFog Inventory by Category across Corpus:")
print(f"  Winter Core (Dec-Jan) : {inv_df['is_winter_core'].sum()} days | {inv_df[inv_df['is_winter_core']]['station_events_count'].sum():,} events")
print(f"  Feb Tail              : {inv_df['is_feb_tail'].sum()} days | {inv_df[inv_df['is_feb_tail']]['station_events_count'].sum():,} events")
print(f"  Monsoon (Jun-Sep)     : {inv_df['is_monsoon'].sum()} days | {inv_df[inv_df['is_monsoon']]['station_events_count'].sum():,} events")
print(f"  Other Shoulder Months : {(~inv_df['is_winter_core'] & ~inv_df['is_feb_tail'] & ~inv_df['is_monsoon']).sum()} days | "
      f"{inv_df[~inv_df['is_winter_core'] & ~inv_df['is_feb_tail'] & ~inv_df['is_monsoon']]['station_events_count'].sum():,} events")

con.close()
