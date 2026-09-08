-- Rollback 014: Drop notification station scope column and index
DROP INDEX IF EXISTS idx_notifications_station_state;
ALTER TABLE notifications DROP COLUMN station_code;
