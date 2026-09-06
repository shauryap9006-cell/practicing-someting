# -*- coding: utf-8 -*-
"""Per-split target bounds, units audit, quality-gate check, and era-null-rate confounder scan."""
import sqlite3, gzip, shutil, json, sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd
from data.db import Database, get_db
from ml.vocab import StationVocab
from ml.train_v2 import build_v2_dataset, get_full_corpus_splits
from ml.features import FEATURE_NAMES_V2

db_path = "data/railtwin.db"
con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row

def cols(t): return [r["name"] for r in con.execute(f"PRAGMA table_info({t})")]
def find_col(t, cands):
    have = set(cols(t))
    for c in cands:
        if c in have: return c

rcol = find_col("station_events", ["run_date", "date"])
dcol = find_col("station_events", ["delay_arr_min", "delay_min", "arr_delay", "delay", "arrival_delay", "delay_minutes"])
tcol = find_col("station_events", ["train_no", "train_number"])

print("="*72)
print("1. TARGET DISTRIBUTION BY ERA & SPLIT IN STATION_EVENTS")
print("="*72)

# Era query on raw station_events
for era_name, condition in [
    ("recovered_2025", f"{rcol} < '2025-07-01'"),
    ("recent_2026",    f"{rcol} >= '2025-07-01'"),
    ("total_corpus",   "1=1"),
]:
    r = con.execute(f"""
        SELECT COUNT(*) n, MIN({dcol}) mn, AVG({dcol}) av, MAX({dcol}) mx,
               AVG(CASE WHEN {dcol} > 600 OR {dcol} < -120 THEN 1.0 ELSE 0.0 END) oob,
               AVG(CASE WHEN {dcol} > 720 OR {dcol} < -180 THEN 1.0 ELSE 0.0 END) severe_oob
        FROM station_events WHERE {condition}""").fetchone()
    print(f"  {era_name:18s} n={r['n']:>9,} min={r['mn']:>8.1f} avg={r['av']:>8.2f} max={r['mx']:>8.1f} "
          f"oob[-120,600]={r['oob']:.4%} severe[-180,720]={r['severe_oob']:.4%}")

# Splits target distribution in dataset sequences
db_inst = get_db()
vocab = StationVocab.from_db(db_path)
splits = get_full_corpus_splits(db_inst)

print("\nPer-Split Target Distribution in V2 Datasets (Sampled/Built):")
for split_name, allowed in [
    ("TRAIN (2025-02-08..2025-11-02)", splits["train_dates"]),
    ("VAL   (2025-11-06..2026-08-29)", splits["val_dates"]),
    ("BENCH (Fog 100 days)",           splits["bench_fog_dates"]),
]:
    ds = build_v2_dataset(db_inst, vocab, allowed_dates=allowed, max_samples=5000)
    targets = np.array([ds[i]["target"].item() for i in range(len(ds))])
    dates = [ds.dates[i] for i in range(len(ds))]
    df_split = pd.DataFrame({"target": targets, "run_date": dates})
    
    for era in ("recovered_2025", "recent_2026"):
        sub = df_split[df_split["run_date"] < "2025-07-01"] if era == "recovered_2025" else df_split[df_split["run_date"] >= "2025-07-01"]
        if len(sub) > 0:
            oob = ((sub["target"] > 600) | (sub["target"] < -120)).mean()
            print(f"  {split_name[:12]} [{era:15s}] N={len(sub):>6,} min={sub['target'].min():>6.1f} "
                  f"avg={sub['target'].mean():>6.2f} max={sub['target'].max():>6.1f} oob={oob:.4%}")

print("\n" + "="*72)
print("2. UNITS AUDIT: PAIRED 2025 vs 2026 TRAIN DELAYS")
print("="*72)
sample_trains = [r[0] for r in con.execute("""
    SELECT se25.train_no
    FROM (SELECT DISTINCT train_no FROM station_events WHERE run_date < '2025-07-01') se25
    JOIN (SELECT DISTINCT train_no FROM station_events WHERE run_date >= '2025-07-01') se26
    ON se25.train_no = se26.train_no LIMIT 10""").fetchall()]

print(f"Sample trains present in BOTH eras: {sample_trains}")
for t_no in sample_trains[:5]:
    r25 = con.execute(f"SELECT run_date, station_code, {dcol} FROM station_events WHERE train_no=? AND run_date < '2025-07-01' LIMIT 2", (t_no,)).fetchall()
    r26 = con.execute(f"SELECT run_date, station_code, {dcol} FROM station_events WHERE train_no=? AND run_date >= '2025-07-01' LIMIT 2", (t_no,)).fetchall()
    print(f"\nTrain {t_no}:")
    for r in r25:
        print(f"  [2025 Era] Date={r['run_date']} Station={r['station_code']:6s} Delay={r[dcol]:>6.1f} min")
    for r in r26:
        print(f"  [2026 Era] Date={r['run_date']} Station={r['station_code']:6s} Delay={r[dcol]:>6.1f} min")

print("\n" + "="*72)
print("3. QUALITY-GATE BYPASS & BACKFILL TRACE")
print("="*72)
# Check collector/quality.py or backfill scripts
for script_name in ["collector/quality.py", "scripts/clean_and_curate_real_data.py", "scripts/ingest_bulk_csv.py", "data/db.py"]:
    p = Path(script_name)
    if p.exists():
        src = p.read_text(encoding="utf-8", errors="replace")
        has_bounds = "delay_min" in src or "bounds" in src or "720" in src or "600" in src or "-120" in src
        print(f"  {script_name:36s} exists=True, contains delay bounds check={has_bounds}")

# Check git log for route-join backfill
try:
    res = subprocess.run(["git", "log", "-n", "5", "--oneline", "--", "data/railtwin.db*"], capture_output=True, text=True)
    print("\nRecent database commits:")
    print(res.stdout.strip() or "No specific db commits in git log")
except Exception as e:
    print(f"git log failed: {e}")

print("\n" + "="*72)
print("4. FEATURE NULL-RATE & ERA-CONFOUNDER SCAN")
print("="*72)
# Evaluate null rate across 2025 vs 2026 in constructed V2 dataset
ds_full = build_v2_dataset(db_inst, vocab, max_samples=10000)
ctx_matrix = np.array([ds_full[i]["ctx"].numpy() for i in range(len(ds_full))])
dates_full = ds_full.dates[:len(ctx_matrix)]
df_ctx = pd.DataFrame(ctx_matrix, columns=FEATURE_NAMES_V2)
df_ctx["run_date"] = dates_full
df_ctx["is_2025"] = df_ctx["run_date"] < "2025-07-01"

print(f"Evaluated N={len(df_ctx):,} sequences (2025: {(df_ctx['is_2025']).sum():,}, 2026: {(~df_ctx['is_2025']).sum():,})")
confounders = []
for f in FEATURE_NAMES_V2:
    null_25 = df_ctx[df_ctx["is_2025"]][f].isna().mean()
    null_26 = df_ctx[~df_ctx["is_2025"]][f].isna().mean()
    zero_25 = (df_ctx[df_ctx["is_2025"]][f] == 0.0).mean()
    zero_26 = (df_ctx[~df_ctx["is_2025"]][f] == 0.0).mean()
    gap_null = abs(null_25 - null_26)
    gap_zero = abs(zero_25 - zero_26)
    flag = ""
    if gap_null > 0.30:
        flag = " <<< ERA-CONFOUNDER (NULL GAP > 30%)"
        confounders.append((f, "null_gap", gap_null))
    elif gap_zero > 0.30:
        flag = " <<< ERA-DRIFT (ZERO GAP > 30%)"
    print(f"  {f:35s} null25={100*null_25:5.1f}% null26={100*null_26:5.1f}% | zero25={100*zero_25:5.1f}% zero26={100*zero_26:5.1f}%{flag}")

print(f"\nConfounders with era-dependent null-rate gap > 30%: {confounders if confounders else 'NONE (0 features)'}")
con.close()
