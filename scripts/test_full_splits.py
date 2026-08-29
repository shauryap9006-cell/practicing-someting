import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from data.db import get_db
from ml.evaluate_v2 import corridor_fog_days, blocked_fog_holdout
from ml.vocab import StationVocab

db = get_db()
vocab = StationVocab.from_db()

with db.transaction() as cur:
    cur.execute("SELECT date, station_code, fog_flag FROM weather")
    w_df = pd.DataFrame([dict(r) for r in cur.fetchall()])
    cur.execute("SELECT DISTINCT run_date FROM station_events ORDER BY run_date")
    all_dates = [r["run_date"] for r in cur.fetchall()]

fog_days_set = corridor_fog_days(w_df, min_days=10)
non_fog_dates, fog_holdout_dates = blocked_fog_holdout(all_dates, fog_days_set, buffer_days=1)

print(f"Total dates in events: {len(all_dates)}")
print(f"Non-fog dates: {len(non_fog_dates)}")
print(f"Fog holdout dates (benchmark): {len(fog_holdout_dates)}")

# Split non_fog_dates into train (85%) and val (15%)
n_val_dates = max(10, int(len(non_fog_dates) * 0.15))
train_dates = non_fog_dates[:-n_val_dates]
val_dates = non_fog_dates[-n_val_dates:]

print(f"\n3-way Split:")
print(f"  Train:     {len(train_dates)} days ({train_dates[0]} to {train_dates[-1]})")
print(f"  Val:       {len(val_dates)} days ({val_dates[0]} to {val_dates[-1]})")
print(f"  Fog Bench: {len(fog_holdout_dates)} days ({fog_holdout_dates[0]} to {fog_holdout_dates[-1]})")

# Verify non-overlap
train_set = set(train_dates)
val_set = set(val_dates)
bench_set = set(fog_holdout_dates)

assert not (train_set & val_set), "Train and Val overlap!"
assert not (train_set & bench_set), "Train and Bench overlap!"
assert not (val_set & bench_set), "Val and Bench overlap!"
print("\n[PASS] Strict 0-overlap assertion across Train, Val, and Fog Benchmark verified!")
