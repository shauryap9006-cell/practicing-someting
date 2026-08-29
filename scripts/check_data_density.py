"""Check data density per date."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.db import get_db
db = get_db()
with db.transaction() as cur:
    cur.execute("SELECT run_date, COUNT(*) as cnt FROM station_events GROUP BY run_date ORDER BY run_date")
    rows = cur.fetchall()
print("Run dates with data:")
for r in rows[:5]:
    print(f"  {r['run_date']}: {r['cnt']:,} events")
print("  ...")
for r in rows[-10:]:
    print(f"  {r['run_date']}: {r['cnt']:,} events")
print(f"Total distinct days: {len(rows)}")
