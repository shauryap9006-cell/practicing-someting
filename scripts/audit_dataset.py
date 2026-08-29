"""Dataset audit script: measures sizes under different split windows."""
from __future__ import annotations
import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import get_db
from ml.vocab import StationVocab
from ml.train_v2 import build_v2_dataset

db = get_db()
with db.transaction() as cur:
    cur.execute("SELECT MIN(run_date) as min_d, MAX(run_date) as max_d FROM station_events")
    row = cur.fetchone()
    cur.execute("SELECT COUNT(*) as cnt FROM station_events")
    total = cur.fetchone()

min_d = row["min_d"]
max_d = row["max_d"]
print(f"Events date range: {min_d} -> {max_d}")
print(f"Total events: {total['cnt']:,}")

# 3-way temporal split: train 70% / val 15% / bench 15% of calendar days
max_dt = datetime.date.fromisoformat(max_d)
min_dt = datetime.date.fromisoformat(min_d)
total_days = (max_dt - min_dt).days

bench_start_dt = max_dt - datetime.timedelta(days=max(6, total_days // 7))
val_start_dt = bench_start_dt - datetime.timedelta(days=max(6, total_days // 7))
train_end_dt = val_start_dt - datetime.timedelta(days=1)
train_start_dt = min_dt

print(f"\nProposed 3-way temporal splits (no overlap):")
print(f"  Train:     {train_start_dt} -> {train_end_dt}")
print(f"  Val:       {val_start_dt}   -> {bench_start_dt - datetime.timedelta(days=1)}")
print(f"  Benchmark: {bench_start_dt}  -> {max_dt}")

vocab = StationVocab.from_db()
train_ds = build_v2_dataset(db, vocab, str(train_start_dt), str(train_end_dt))
val_ds = build_v2_dataset(db, vocab, str(val_start_dt), str(bench_start_dt - datetime.timedelta(days=1)))
bench_ds = build_v2_dataset(db, vocab, str(bench_start_dt), str(max_dt))

print(f"\nDataset sizes:")
print(f"  Train: {len(train_ds):,}")
print(f"  Val:   {len(val_ds):,}")
print(f"  Bench: {len(bench_ds):,}")
print(f"  Train/Val ratio: {len(train_ds)/max(1,len(val_ds)):.1f}x (must be > 5x)")

# Also check the OLD split to confirm BUG C and D
old_max_dt = datetime.date.fromisoformat(max_d)
old_val_start_dt = old_max_dt - datetime.timedelta(days=6)
old_train_end_dt = old_val_start_dt - datetime.timedelta(days=1)
old_train_start_dt = max(datetime.date.fromisoformat(min_d), old_train_end_dt - datetime.timedelta(days=21))

print(f"\nOLD broken split (Bug C+D confirmation):")
print(f"  Old Train:  {old_train_start_dt} -> {old_train_end_dt}")
print(f"  Old Val:    {old_val_start_dt}   -> {max_d}")
old_train_ds = build_v2_dataset(db, vocab, str(old_train_start_dt), str(old_train_end_dt))
old_val_ds = build_v2_dataset(db, vocab, str(old_val_start_dt), str(max_d))
print(f"  Old Train sequences: {len(old_train_ds):,}")
print(f"  Old Val sequences:   {len(old_val_ds):,}")
if len(old_train_ds) < len(old_val_ds):
    print("  >>> BUG C CONFIRMED: Training set SMALLER than validation set!")
