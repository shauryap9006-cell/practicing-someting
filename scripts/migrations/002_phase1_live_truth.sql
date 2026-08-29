-- RailTwin-X — Migration 002: Phase 1 Live Truth & Operational Core
-- Implements tables for Timetable Manager, Set-In/Set-Out Actuals, Platform State Machines,
-- Block Status, Shunting Movements, and Day Planner Changesets.

PRAGMA foreign_keys = ON;

-- 1. Timetable Versions & Working Timetable Entries (Module A1)
CREATE TABLE IF NOT EXISTS timetable_versions (
  id TEXT PRIMARY KEY,
  version_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'published', 'archived')),
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  description TEXT,
  created_by TEXT NOT NULL,
  published_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timetable_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version_id TEXT NOT NULL,
  train_no TEXT NOT NULL,
  train_name TEXT NOT NULL,
  train_type TEXT NOT NULL CHECK(train_type IN ('express', 'passenger', 'freight', 'emu', 'special')),
  direction TEXT NOT NULL CHECK(direction IN ('UP', 'DOWN')),
  station_code TEXT NOT NULL,
  stop_seq INTEGER NOT NULL,
  sched_arr TEXT,
  sched_dep TEXT,
  halt_min INTEGER NOT NULL DEFAULT 2,
  platform_default INTEGER NOT NULL DEFAULT 1,
  days_of_run TEXT NOT NULL DEFAULT 'DAILY', -- e.g. 'MON,WED,FRI' or 'DAILY'
  is_cancelled INTEGER NOT NULL DEFAULT 0,
  cancellation_reason TEXT,
  FOREIGN KEY (version_id) REFERENCES timetable_versions(id) ON DELETE CASCADE,
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_tt_entries_version ON timetable_entries(version_id, train_no);
CREATE INDEX IF NOT EXISTS idx_tt_entries_stn ON timetable_entries(station_code, sched_arr);

-- 2. Set-In / Set-Out Operational Ground Truth Events (Module A4 - Bucket C Moat)
CREATE TABLE IF NOT EXISTS ad_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  train_no TEXT NOT NULL,
  station_code TEXT NOT NULL,
  event_kind TEXT NOT NULL CHECK(event_kind IN ('setin', 'setout')),
  actual_ts TEXT NOT NULL,
  platform INTEGER NOT NULL,
  predicted_ts TEXT,
  discrepancy_min REAL DEFAULT 0.0,
  discrepancy_flag INTEGER DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'human' CHECK(source IN ('human', 'inferred', 'gps')),
  confirmed_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ad_events_run ON ad_events(run_id, event_kind);
CREATE INDEX IF NOT EXISTS idx_ad_events_stn_ts ON ad_events(station_code, actual_ts);

-- 3. Platform States & Dynamic Allocations (Module A3)
CREATE TABLE IF NOT EXISTS platform_states (
  station_code TEXT NOT NULL,
  platform INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'FREE' CHECK(state IN ('FREE', 'OCCUPIED', 'BLOCKED_MAINT', 'OUT_OF_SERVICE')),
  occupied_by_train TEXT,
  since TEXT NOT NULL,
  reason TEXT,
  updated_by TEXT NOT NULL,
  PRIMARY KEY (station_code, platform)
);

CREATE TABLE IF NOT EXISTS platform_assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station_code TEXT NOT NULL,
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL,
  platform INTEGER NOT NULL,
  assigned_arr TEXT NOT NULL,
  assigned_dep TEXT NOT NULL,
  is_locked INTEGER NOT NULL DEFAULT 0,
  locked_by TEXT,
  status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK(status IN ('SCHEDULED', 'ACTIVE', 'COMPLETED', 'CANCELLED')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pf_assign_stn ON platform_assignments(station_code, run_date, platform);

-- 4. Block Section & Line Clear Status (Module A5)
CREATE TABLE IF NOT EXISTS block_status (
  block_id TEXT PRIMARY KEY,
  from_code TEXT NOT NULL,
  to_code TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'CLEAR' CHECK(state IN ('CLEAR', 'OCCUPIED', 'BLOCKED', 'CAUTION')),
  occupied_by_train TEXT,
  line_clear_granted_to TEXT,
  granted_by TEXT,
  since TEXT NOT NULL,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_block_status_section ON block_status(from_code, to_code);

-- 5. Shunting & Non-Timetable Loco Movement Log (Module A6)
CREATE TABLE IF NOT EXISTS shunting_moves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station_code TEXT NOT NULL,
  move_type TEXT NOT NULL CHECK(move_type IN ('loco_attach', 'loco_detach', 'rake_release', 'yard_shunt', 'empty_haul')),
  loco_id TEXT NOT NULL,
  rake_id TEXT,
  from_track TEXT NOT NULL,
  to_track TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'REQUESTED' CHECK(status IN ('REQUESTED', 'APPROVED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
  notes TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shunting_stn_time ON shunting_moves(station_code, start_time);

-- 6. Planner Changesets & What-If History (Module C4)
CREATE TABLE IF NOT EXISTS planner_changesets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station_code TEXT NOT NULL,
  plan_date TEXT NOT NULL,
  changeset_json TEXT NOT NULL,
  sim_result_json TEXT NOT NULL DEFAULT '{}',
  interlock_passed INTEGER NOT NULL DEFAULT 1,
  applied_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_planner_changesets_stn ON planner_changesets(station_code, plan_date);
