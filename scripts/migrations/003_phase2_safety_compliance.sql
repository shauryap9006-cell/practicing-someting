-- RailTwin-X — Migration 003: Phase 2 Safety & Compliance
-- Creates possessions, incidents, sop_runs, and level_crossings.

PRAGMA foreign_keys = ON;

-- 1. Caution Orders Index (Module D2)
CREATE INDEX IF NOT EXISTS idx_tsr_section_status ON speed_restrictions(from_code, to_code, status);

-- 2. Permit-to-Work / Track Possessions (Module D3)
CREATE TABLE IF NOT EXISTS possessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  possession_type TEXT NOT NULL CHECK(possession_type IN ('BLOCK_SECTION', 'PLATFORM', 'OHE_LINE', 'YARD_TRACK')),
  element_id TEXT NOT NULL,
  station_code TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  work_type TEXT NOT NULL CHECK(work_type IN ('P_WAY', 'OHE_TRACTION', 'S_AND_T', 'BRIDGE_WORK', 'GENERAL')),
  requesting_dept TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'REQUESTED' CHECK(status IN ('REQUESTED', 'GRANTED', 'ACTIVE', 'RESTORED', 'CANCELLED')),
  granted_by TEXT,
  granted_at TEXT,
  restored_by TEXT,
  restored_at TEXT,
  notes TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_possessions_stn_time ON possessions(station_code, start_time, status);

-- 3. Incident & Near-Miss Register (Module D4)
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_type TEXT NOT NULL CHECK(incident_type IN ('SPAD', 'DERAILMENT', 'EQUIPMENT_FAIL', 'NEAR_MISS', 'GATE_BURST', 'OHE_BREAKDOWN', 'TRESPASSING')),
  severity TEXT NOT NULL CHECK(severity IN ('MINOR', 'MAJOR', 'CRITICAL')),
  station_code TEXT NOT NULL,
  location_km REAL,
  train_no TEXT,
  summary TEXT NOT NULL,
  investigation_status TEXT NOT NULL DEFAULT 'OPEN' CHECK(investigation_status IN ('OPEN', 'UNDER_REVIEW', 'CLOSED')),
  action_taken TEXT,
  reported_by TEXT NOT NULL,
  reported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incidents_stn ON incidents(station_code, reported_at);

-- 4. SOP / Emergency Checklist Runner (Module D5)
CREATE TABLE IF NOT EXISTS sop_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id TEXT NOT NULL,
  title TEXT NOT NULL,
  station_code TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'CRITICAL',
  status TEXT NOT NULL DEFAULT 'IN_PROGRESS' CHECK(status IN ('IN_PROGRESS', 'COMPLETED', 'ABORTED')),
  steps_completed_json TEXT NOT NULL DEFAULT '[]',
  started_by TEXT NOT NULL,
  started_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sop_runs_stn ON sop_runs(station_code, status);

-- 5. Level Crossing Status Board (Module D6)
CREATE TABLE IF NOT EXISTS level_crossings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lc_number TEXT NOT NULL UNIQUE,
  station_code TEXT NOT NULL,
  km REAL NOT NULL,
  gate_type TEXT NOT NULL CHECK(gate_type IN ('MANNED_INTERLOCKED', 'MANNED_NON_INTERLOCKED', 'SPECIAL_CLASS', 'UNMANNED')),
  status TEXT NOT NULL DEFAULT 'NORMAL' CHECK(status IN ('NORMAL', 'DEFECTIVE', 'BOOM_DAMAGED', 'INTERLOCK_FAIL', 'MAINTENANCE')),
  last_inspected TEXT NOT NULL,
  gateman_name TEXT,
  contact_phone TEXT,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lc_stn ON level_crossings(station_code, status);
