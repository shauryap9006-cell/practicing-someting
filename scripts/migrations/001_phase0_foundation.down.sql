-- Rollback 001: Drop Phase 0 tables
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS run_snapshots;
DROP TABLE IF EXISTS train_runs;
DROP TABLE IF EXISTS notification_ack;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS handover_log;
DROP TABLE IF EXISTS backups;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
PRAGMA foreign_keys = ON;
