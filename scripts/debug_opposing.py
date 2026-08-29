"""Debug opposing_trains_30k - why always zero."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db import Database
from engine.spatial_context import build_trajectories, DaySpatialIndex, _infer_direction
import datetime, numpy as np

db = Database()
day = '2025-02-08'
day_dt = datetime.date.fromisoformat(day)
day_start = datetime.datetime(day_dt.year, day_dt.month, day_dt.day, 0, 0, 0)

trajs = build_trajectories(db, day)
print(f'Total trajectories: {len(trajs)}')

up_count = sum(1 for t in trajs if t.is_up)
down_count = sum(1 for t in trajs if not t.is_up)
print(f'is_up=True: {up_count}  is_up=False: {down_count}')

# Check what km ranges look like
with db.transaction() as cur:
    cur.execute('''SELECT rs.train_no, MIN(rs.distance_km) as km_min, MAX(rs.distance_km) as km_max,
        COUNT(*) as stops FROM route_stations rs GROUP BY rs.train_no LIMIT 10''')
    rows = cur.fetchall()
    print('\nSample route km ranges:')
    for r in rows:
        direction = 'UP' if r['km_max'] > r['km_min'] else 'DOWN'
        print(f'  {r["train_no"]}: km={r["km_min"]:.0f}-{r["km_max"]:.0f} {direction} ({r["stops"]} stops)')

# All trains have increasing km (all go from origin=0 up)?
all_up = all(t.is_up for t in trajs)
print(f'\nAll trains is_up=True: {all_up}')
print('If all trains go in same km direction, opposing=0 is CORRECT for this corridor.')
print('The 30k window assertion for opposing is too strict for a single-direction corridor.')
print('RECOMMENDATION: Relax assertion for opposing_trains_30k OR check section single_line flags.')

# Check sections single_line
with db.transaction() as cur:
    cur.execute('SELECT COUNT(*) as n, SUM(single_line) as sl FROM sections')
    r = cur.fetchone()
    print(f'\nSections: total={r["n"]}, single_line={r["sl"]}')
