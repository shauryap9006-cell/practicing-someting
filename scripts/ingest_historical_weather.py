"""Ingests full 2021-2025 historical weather dataset into SQLite weather table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config import settings
from data.db import get_db

db = get_db()
print("[INFO] Loading historical weather data from data/weather/corridor_historical_weather_2021_2025.csv...")
df = pd.read_csv("data/weather/corridor_historical_weather_2021_2025.csv")
df["date"] = df["time"].str[:10]

# Apply project fog rule
df["fog_flag"] = (
    (df["temperature"] < settings.FOG_MAX_TEMP_CELSIUS) &
    (df["humidity"] > settings.FOG_MIN_HUMIDITY_PERCENT)
).astype(int)

# Aggregate to daily per station
daily = df.groupby(["date", "station_code"]).agg({
    "temperature": "mean",
    "precipitation": "sum",
    "humidity": "mean",
    "fog_flag": "max",
}).reset_index()

print(f"[INFO] Prepared {len(daily):,} daily weather records across {daily['station_code'].nunique()} stations.")

# Insert into SQLite weather table
records = [
    (
        row["date"],
        row["station_code"],
        round(float(row["temperature"]), 1),
        round(float(row["precipitation"]), 1),
        round(float(row["humidity"]), 1),
        int(row["fog_flag"]),
    )
    for _, row in daily.iterrows()
]

with db.transaction() as cur:
    cur.executemany(
        """
        INSERT OR REPLACE INTO weather (date, station_code, temp, precip_mm, humidity, fog_flag)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        records,
    )

with db.transaction() as cur:
    cur.execute("SELECT MIN(date) as min_d, MAX(date) as max_d, COUNT(*) as cnt, SUM(fog_flag) as fog_cnt FROM weather")
    r = cur.fetchone()
    print(f"[SUCCESS] SQLite weather table now has: {r['min_d']} to {r['max_d']} ({r['cnt']:,} rows, {r['fog_cnt']:,} fog station-days).")
