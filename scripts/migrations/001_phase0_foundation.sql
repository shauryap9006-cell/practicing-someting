-- RailTwin-X — Migration 001: Phase 0 Foundation & Bucket C Spine
-- Implements tables for RBAC, Audit Trail, Backup Automation, Handover Logbook, Notification Center, and Live Telemetry Snapshots.

PRAGMA foreign_keys = ON;

-- 0. Schema Migrations Ledger
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

-- 1. Roles & Permissions (Module I1)
CREATE TABLE IF NOT EXISTS roles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  permissions_json TEXT NOT NULL DEFAULT '[]'
);

-- 2. Users (Module I1)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE,
  password_hash TEXT NOT NULL,
  role_id TEXT NOT NULL,
  station_code TEXT NOT NULL DEFAULT 'NDLS',
  full_name TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_station ON users(station_code);

-- 3. User Roles Mapping (Module I1)
CREATE TABLE IF NOT EXISTS user_roles (
  user_id TEXT NOT NULL,
  role_id TEXT NOT NULL,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- 4. Cryptographic Hash-Chained Audit Log (Module I3)
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  action TEXT NOT NULL,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  before_state TEXT,
  after_state TEXT,
  row_hash TEXT NOT NULL,
  prev_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_table ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id);

-- 5. Database Backups Ledger (Module I5)
CREATE TABLE IF NOT EXISTS backups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  backup_ts TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  row_counts_json TEXT,
  status TEXT NOT NULL DEFAULT 'SUCCESS',
  checksum_sha256 TEXT NOT NULL
);

-- 6. Digital Shift Handover Logbook (Module I2)
CREATE TABLE IF NOT EXISTS handover_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station_code TEXT NOT NULL,
  shift_date TEXT NOT NULL,
  shift_type TEXT NOT NULL CHECK(shift_type IN ('morning', 'afternoon', 'night')),
  outgoing_user_id TEXT NOT NULL,
  incoming_user_id TEXT,
  outgoing_signed_at TEXT,
  incoming_acked_at TEXT,
  open_incidents_json TEXT NOT NULL DEFAULT '[]',
  active_srs_json TEXT NOT NULL DEFAULT '[]',
  active_possessions_json TEXT NOT NULL DEFAULT '[]',
  crew_exceptions_json TEXT NOT NULL DEFAULT '[]',
  operational_notes TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'signed', 'acknowledged')),
  FOREIGN KEY (outgoing_user_id) REFERENCES users(id),
  FOREIGN KEY (incoming_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_handover_station_date ON handover_log(station_code, shift_date);

-- 7. Notification Center & Escalation Ladder (Module I4)
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  target_role TEXT,
  severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  state TEXT NOT NULL DEFAULT 'queued' CHECK(state IN ('queued', 'sent', 'escalated', 'acked')),
  created_at TEXT NOT NULL,
  escalated_at TEXT,
  acked_at TEXT,
  acked_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_notifications_role_state ON notifications(target_role, state);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);

CREATE TABLE IF NOT EXISTS notification_ack (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  notif_id INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'in_app',
  ack_ts TEXT NOT NULL,
  notes TEXT,
  FOREIGN KEY (notif_id) REFERENCES notifications(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notif_ack_notif ON notification_ack(notif_id);

-- 8. Bucket C: Train Runs and Live Telemetry Snapshots
CREATE TABLE IF NOT EXISTS train_runs (
  run_id TEXT PRIMARY KEY,
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL,
  origin TEXT,
  dest TEXT,
  source TEXT NOT NULL DEFAULT 'rapidapi' CHECK(source IN ('rapidapi', 'synthetic', 'manual')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_train_runs_train_date ON train_runs(train_no, run_date);

CREATE TABLE IF NOT EXISTS run_snapshots (
  snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  station_code TEXT NOT NULL,
  sch_arr TEXT,
  sch_dep TEXT,
  exp_arr TEXT,
  exp_dep TEXT,
  delay_min INTEGER DEFAULT 0,
  last_loc_station TEXT,
  lat REAL,
  lng REAL,
  raw_json TEXT,
  source TEXT NOT NULL DEFAULT 'rapidapi' CHECK(source IN ('rapidapi', 'synthetic', 'manual')),
  FOREIGN KEY (run_id) REFERENCES train_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_run_ts ON run_snapshots(run_id, ts);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON run_snapshots(ts);
