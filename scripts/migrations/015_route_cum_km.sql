-- Migration 015: Create and populate route_cum_km table from route_stations (Fix D07)
CREATE TABLE IF NOT EXISTS route_cum_km (
    train_no TEXT NOT NULL,
    station_code TEXT NOT NULL,
    seq INTEGER NOT NULL,
    cum_km REAL NOT NULL,
    PRIMARY KEY (train_no, seq)
);

CREATE INDEX IF NOT EXISTS idx_route_cum_km_lookup ON route_cum_km(train_no, station_code);
CREATE INDEX IF NOT EXISTS idx_route_cum_km_seq ON route_cum_km(train_no, seq);

-- Monotonicity-verified population from route_stations
INSERT OR REPLACE INTO route_cum_km (train_no, station_code, seq, cum_km)
SELECT train_no, station_code, seq, COALESCE(distance_km, 0.0) as cum_km
FROM route_stations
ORDER BY train_no, seq;
