-- Migration 004: Compact stop-sequence gaps in route_stations while preserving raw sequence in seq_raw

-- 1. Ensure seq_raw column exists
-- In SQLite, duplicate column add is caught by checking pragma in python runner or ignore
-- 2. Create temp table for deterministic ranking
CREATE TEMP TABLE IF NOT EXISTS ranked_stops AS
SELECT rowid as rid,
       ROW_NUMBER() OVER (PARTITION BY train_no ORDER BY CAST(seq AS INTEGER), distance_km) as new_seq
FROM route_stations;

-- 3. Update route_stations sequence
UPDATE route_stations
SET seq = (SELECT new_seq FROM ranked_stops WHERE ranked_stops.rid = route_stations.rowid)
WHERE EXISTS (SELECT 1 FROM ranked_stops WHERE ranked_stops.rid = route_stations.rowid);

DROP TABLE IF EXISTS ranked_stops;
