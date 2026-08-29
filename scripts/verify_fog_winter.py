import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config import settings
from data.db import get_db

df = pd.read_csv("data/weather/corridor_historical_weather_2021_2025.csv")
df["date"] = df["time"].str[:10]
df["hour"] = df["time"].str[11:13].astype(int)

# Apply project fog rule from settings: temp < 18.0 and humidity > 85.0
df["fog_flag"] = (
    (df["temperature"] < settings.FOG_MAX_TEMP_CELSIUS) &
    (df["humidity"] > settings.FOG_MIN_HUMIDITY_PERCENT)
).astype(int)

print(f"Total historical hourly observations with fog: {df['fog_flag'].sum():,}")

# Daily aggregation per station
daily = df.groupby(["date", "station_code"]).agg({
    "fog_flag": "max",
    "temperature": "mean",
    "humidity": "mean",
    "precipitation": "sum"
}).reset_index()

print(f"Total station-days with fog: {daily['fog_flag'].sum():,}")

# Corridor fog days: days where at least 4 stations had fog
corridor_fog = daily.groupby("date")["fog_flag"].sum()
corridor_fog_days = corridor_fog[corridor_fog >= 4].index.tolist()
print(f"Total corridor-level fog days (>=4 stations): {len(corridor_fog_days)}")

# Winter 2025-2026 fog days (Dec 2025 to Jan 2026)
winter_fog = [d for d in corridor_fog_days if d >= "2025-12-01" and d <= "2026-01-31"]
print(f"Corridor fog days in Dec 2025 - Jan 2026 winter: {len(winter_fog)}")
print("Sample winter fog days:", winter_fog[:10])

# Check how many station events exist on these winter fog days in SQLite DB
db = get_db()
with db.transaction() as cur:
    cur.execute("SELECT COUNT(*) as cnt FROM station_events WHERE run_date >= '2025-12-01' AND run_date <= '2026-01-31'")
    cnt_winter = cur.fetchone()["cnt"]
    
print(f"Total station_events in DB during Dec 2025 - Jan 2026 winter: {cnt_winter:,}")
