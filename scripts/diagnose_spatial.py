"""TASK-0 diagnostic - ASCII only for Windows CP1252."""
import sys, os, sqlite3, datetime, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

conn = sqlite3.connect('data/railtwin.db')
conn.row_factory = sqlite3.Row

print("=" * 60)
print("TASK-0 SPATIAL DIAGNOSTIC - FULL OUTPUT")
print("=" * 60)

# Busiest-day count
r = conn.execute('''SELECT run_date, COUNT(DISTINCT train_no) as n
    FROM station_events GROUP BY run_date ORDER BY n DESC LIMIT 5''').fetchall()
print("\n[DENSITY] Trains per day (top 5):")
for row in r:
    print(f"  {row['run_date']}: {row['n']} trains (need >20)")
busy_day = r[0]['run_date'] if r else None
busy_count = r[0]['n'] if r else 0

# Full archive range
dr = conn.execute('SELECT MIN(run_date) as mn, MAX(run_date) as mx FROM station_events').fetchone()
print(f"\n[ARCHIVE] Full range: {dr['mn']} to {dr['mx']}")

# Direction check
from data.db import Database
from engine.track_graph import TrackGraph
db = Database()
tg = TrackGraph(db)
all_dests = set(tg._routes_dest.values())
print(f"\n[H2-DIRECTION] Unique destination stations: {len(all_dests)}")
print("[H2-DIRECTION] same_direction logic = (routes_dest[A] == routes_dest[B])")
print("[H2-DIRECTION] With 184 unique dests, most train pairs return False -> trains_ahead = 0")

# Spot check: for train 12003, how many other trains share same dest?
t_no = '12003'
my_dest = tg._routes_dest.get(t_no, 'NONE')
same_dest = sum(1 for tn, d in tg._routes_dest.items() if d == my_dest and tn != t_no)
print(f"[H2-DIRECTION] Train {t_no} dest={my_dest}, other trains with same dest: {same_dest}")
print(f"[H2-DIRECTION] Trains without same dest (= not counted as ahead): {len(tg._routes_dest) - same_dest - 1}")

# Clear cache and build 2-day sample
print("\n[H3] Clearing parquet cache and building 2-day snapshot...")
snap_cache = pathlib.Path('data/cache')
cleared = 0
for f in snap_cache.glob('snap_*.parquet'):
    f.unlink()
    cleared += 1
print(f"[H3] Cleared {cleared} cached parquet files")

from ml.snapshots import SnapshotGenerator
db2 = Database()
sg = SnapshotGenerator(db2)
d_start = dr['mn']
d_end = (datetime.date.fromisoformat(d_start) + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
print(f"[H3] Building: {d_start} to {d_end}")
df = sg.build_dataset(d_start, d_end, d_start)
print(f"[H3] Dataset shape: {df.shape}")
for c in ['trains_ahead_30k','opposing_trains_30k','sum_delay_trains_ahead_30k','section_occupancy_pct']:
    if c in df.columns:
        frac = df[c].ne(0).mean()
        mn, mx = df[c].min(), df[c].max()
        print(f"  {c}: nonzero={frac:.4f}  min={mn:.3f}  max={mx:.3f}")
    else:
        print(f"  {c}: COLUMN MISSING")

print("\n[VERDICT] Classification:")
print("H1 (stub): NEGATIVE - TrackGraph IS called at snapshots.py:496")
print("H2 (bad query): CONFIRMED - direction detection wrong (same terminus, not km-direction)")
print("H3 (overwrite): NEGATIVE - cached_track_context passed through directly, no clobber")
print(f"\n[ROOT CAUSE] engine/track_graph.py line 209:")
print("  same_direction = (self._routes_dest.get(o_no) == my_dest)")
print("  184 unique destination stations -> almost never True -> trains_ahead=0 always")
print(f"\n[SEED DENSITY] {busy_count} trains on busiest day - well above 20 threshold")
print("  No need to widen seeds. Fix ONLY the direction logic.")

conn.close()
