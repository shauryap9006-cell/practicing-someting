-- Migration 006: Standardize single-letter station codes with alias mapping table

CREATE TABLE IF NOT EXISTS station_aliases (
    alt_code TEXT PRIMARY KEY,
    canonical_code TEXT NOT NULL,
    full_name TEXT NOT NULL
);

INSERT OR REPLACE INTO station_aliases (alt_code, canonical_code, full_name) VALUES
    ('R', 'RPR', 'Raipur Junction'),
    ('J', 'JLN', 'Jalna'),
    ('S', 'SRPT', 'Shrirangapatna'),
    ('G', 'GON', 'Gondia Jn');

-- Update any remaining references
UPDATE stations SET code = 'RPR' WHERE code = 'R';
UPDATE route_stations SET station_code = 'RPR' WHERE station_code = 'R';
UPDATE station_events SET station_code = 'RPR' WHERE station_code = 'R';

UPDATE stations SET code = 'JLN' WHERE code = 'J';
UPDATE route_stations SET station_code = 'JLN' WHERE station_code = 'J';
UPDATE station_events SET station_code = 'JLN' WHERE station_code = 'J';

UPDATE stations SET code = 'SRPT' WHERE code = 'S';
UPDATE route_stations SET station_code = 'SRPT' WHERE station_code = 'S';
UPDATE station_events SET station_code = 'SRPT' WHERE station_code = 'S';

UPDATE stations SET code = 'GON' WHERE code = 'G';
UPDATE route_stations SET station_code = 'GON' WHERE station_code = 'G';
UPDATE station_events SET station_code = 'GON' WHERE station_code = 'G';
