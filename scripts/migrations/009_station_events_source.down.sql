-- Rollback 009: Remove source column from station_events
ALTER TABLE station_events DROP COLUMN source;
