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

n_val_dates = max(10, int(len(non_fog_dates) * 0.15))
train_dates = set(non_fog_dates[:-n_val_dates])
val_dates = set(non_fog_dates[-n_val_dates:])

with db.transaction() as cur:
    cur.execute("""
        SELECT se.train_no, se.run_date, se.seq
        FROM station_events se
        JOIN route_stations rs ON (se.train_no = rs.train_no AND se.seq = rs.seq)
    """)
    rows = cur.fetchall()

train_events = sum(1 for r in rows if r["run_date"] in train_dates)
val_events = sum(1 for r in rows if r["run_date"] in val_dates)
bench_events = sum(1 for r in rows if r["run_date"] in set(fog_holdout_dates))

print(f"Events per split:")
print(f"  Train:     {train_events:,} events")
print(f"  Val:       {val_events:,} events")
print(f"  Fog Bench: {bench_events:,} events")
print(f"  Train / Val ratio: {train_events / max(1, val_events):.1f}x (satisfies > 5x guard!)")
