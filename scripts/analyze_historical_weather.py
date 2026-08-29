import pandas as pd
from pathlib import Path

df = pd.read_csv("data/weather/corridor_historical_weather_2021_2025.csv")
print(f"Historical weather rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f"Date range: {df['time'].min()} to {df['time'].max()}")
print(f"Unique stations: {df['station_code'].unique()}")

df['date'] = df['time'].str[:10]
df['year'] = df['time'].str[:4]
df['month'] = df['time'].str[5:7]

fog_by_month = df.groupby(['year', 'month'])['is_fog'].sum()
print("\nFog hours by Year-Month in 2021-2025:")
for (y, m), val in fog_by_month.items():
    if val > 0:
        print(f"  {y}-{m}: {val:,} fog hours")
