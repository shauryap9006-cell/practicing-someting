-- Rollback 011: Drop live positions and live delay ledger tables
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS live_delay_ledger;
DROP TABLE IF EXISTS live_positions;
PRAGMA foreign_keys = ON;
