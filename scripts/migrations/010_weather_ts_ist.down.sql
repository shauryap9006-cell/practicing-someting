-- Rollback 010: Remove hourly weather columns from weather table
ALTER TABLE weather DROP COLUMN precipitation;
ALTER TABLE weather DROP COLUMN temperature_2m;
ALTER TABLE weather DROP COLUMN relative_humidity_2m;
ALTER TABLE weather DROP COLUMN wind_speed_10m;
ALTER TABLE weather DROP COLUMN visibility;
ALTER TABLE weather DROP COLUMN ts_ist;
