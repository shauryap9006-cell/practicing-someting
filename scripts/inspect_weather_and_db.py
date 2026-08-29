import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import get_db
import pandas as pd

db = get_db()
print("=== TABLES IN DB ===")
with db.transaction() as cur:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in cur.fetchall()]
    print(tables)
    
    for t in tables:
        cur.execute(f"SELECT count(*) as cnt FROM {t}")
        c = cur.fetchone()['cnt']
        print(f"  {t}: {c:,} rows")

print("\n=== CHECKING WEATHER TABLE ===")
with db.transaction() as cur:
    cur.execute("SELECT MIN(date) as min_d, MAX(date) as max_d, count(*) as cnt, sum(fog_flag) as fog_cnt FROM weather")
    r = cur.fetchone()
    print(dict(r))
    
    cur.execute("SELECT substr(date, 1, 7) as ym, count(*) as cnt, sum(fog_flag) as fog_cnt FROM weather GROUP BY ym")
    for r in cur.fetchall():
        print(dict(r))

    cur.execute("SELECT date, count(*) as total_stns, sum(fog_flag) as fog_stns FROM weather GROUP BY date HAVING fog_stns > 0 ORDER BY date")
    fog_days_in_weather = cur.fetchall()
    print(f"\nDays with fog in weather table: {len(fog_days_in_weather)}")
    for r in fog_days_in_weather[:15]:
        print(f"  {r['date']}: {r['fog_stns']}/{r['total_stns']} stations with fog")

print("\n=== CHECKING FILES IN DATA/ DIRECTORY ===")
for p in Path("data").rglob("*"):
    if p.is_file() and not p.name.endswith(".db"):
        print(f"  {p} ({p.stat().st_size:,} bytes)")
