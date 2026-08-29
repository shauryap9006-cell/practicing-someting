"""Debug timestamp columns for trajectory building."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db import Database
db = Database()
day = '2025-02-08'

with db.transaction() as cur:
    cur.execute('''SELECT e.train_no, e.seq, e.sched_arr, e.actual_arr,
        e.event_time, e.collected_at, r.distance_km
        FROM station_events e
        JOIN route_stations r ON e.train_no = r.train_no AND e.seq = r.seq
        WHERE e.run_date = ? AND e.train_no = '1023'
        ORDER BY e.seq''', (day,))
    rows = cur.fetchall()
    print('Train 1023 full event timeline:')
    for r in rows:
        print(f"  seq={r['seq']:2d}  sched_arr={r['sched_arr']}  actual_arr={r['actual_arr']}"
              f"  event_time={r['event_time']}  km={r['distance_km']:.1f}")

print()
print("CONCLUSION: If all timestamps identical -> use sched_arr + run_date to reconstruct timeline")
print("sched_arr is 'HH:MM' -> combine with run_date to get real time")
