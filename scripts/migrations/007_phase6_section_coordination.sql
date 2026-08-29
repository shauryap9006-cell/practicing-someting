-- RailTwin-X — Migration 007: Phase 6 Section Coordination & Multi-Station Topology
-- Implements tables for Corridor Sections, Cross-Station Handoff Locks, and Dynamic Section Advisories.

PRAGMA foreign_keys = ON;

-- 1. Corridor Multi-Station Topology
CREATE TABLE IF NOT EXISTS corridor_sections (
  section_id TEXT PRIMARY KEY,
  from_station TEXT NOT NULL,
  to_station TEXT NOT NULL,
  length_km REAL NOT NULL,
  max_speed_kmph REAL NOT NULL DEFAULT 130.0,
  is_electrified INTEGER NOT NULL DEFAULT 1,
  signaling_type TEXT NOT NULL DEFAULT 'AUTOMATIC_BLOCK' CHECK(signaling_type IN ('AUTOMATIC_BLOCK', 'ABSOLUTE_BLOCK', 'CTC', 'KAVACH_ATP')),
  FOREIGN KEY (from_station) REFERENCES stations(code),
  FOREIGN KEY (to_station) REFERENCES stations(code)
);

CREATE INDEX IF NOT EXISTS idx_corr_sec_stns ON corridor_sections(from_station, to_station);

-- 2. Cross-Station Interlocking Handoff Locks (Module C3)
CREATE TABLE IF NOT EXISTS cross_station_locks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  section_id TEXT NOT NULL,
  from_station TEXT NOT NULL,
  to_station TEXT NOT NULL,
  train_no TEXT NOT NULL,
  lock_state TEXT NOT NULL DEFAULT 'REQUESTED' CHECK(lock_state IN ('REQUESTED', 'GRANTED', 'OCCUPIED', 'RELEASED', 'REJECTED')),
  requested_by TEXT NOT NULL,
  granted_by TEXT,
  granted_at TEXT,
  released_at TEXT,
  notes TEXT,
  FOREIGN KEY (section_id) REFERENCES corridor_sections(section_id)
);

CREATE INDEX IF NOT EXISTS idx_cross_locks_sec ON cross_station_locks(section_id, lock_state);

-- 3. Dynamic Section Precedence Advisories (Module C2)
CREATE TABLE IF NOT EXISTS section_advisories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  section_id TEXT NOT NULL,
  train_no TEXT NOT NULL,
  overtaking_train_no TEXT,
  advisory_type TEXT NOT NULL CHECK(advisory_type IN ('OVERTAKE', 'REGULATION', 'SPEED_HOLD', 'EARLY_DEPARTURE', 'LOOP_DIVERSION')),
  recommended_station TEXT NOT NULL,
  recommended_loop_line INTEGER NOT NULL DEFAULT 2,
  priority_score REAL NOT NULL DEFAULT 1.0,
  details TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'EXECUTED')),
  created_at TEXT NOT NULL,
  executed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sec_adv_stn ON section_advisories(section_id, status);
