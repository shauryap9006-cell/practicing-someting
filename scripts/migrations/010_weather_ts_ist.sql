-- Migration 010: Add ts_ist and hourly weather attributes to weather table (Phase B1)
ALTER TABLE weather ADD COLUMN ts_ist TEXT;
ALTER TABLE weather ADD COLUMN visibility REAL;
ALTER TABLE weather ADD COLUMN wind_speed_10m REAL;
ALTER TABLE weather ADD COLUMN relative_humidity_2m REAL;
ALTER TABLE weather ADD COLUMN temperature_2m REAL;
ALTER TABLE weather ADD COLUMN precipitation REAL;
