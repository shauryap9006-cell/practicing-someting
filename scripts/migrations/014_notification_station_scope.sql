-- Bind notification records to the operational station that generated them.
ALTER TABLE notifications ADD COLUMN station_code TEXT;
CREATE INDEX IF NOT EXISTS idx_notifications_station_state ON notifications(station_code, state, created_at);
