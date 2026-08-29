-- RailTwin-X — Migration 005: Phase 4 Workforce & Crew Intelligence
-- Implements tables for Breathalyzer Tests, Crew CMS Rosters, Staff Shifts, and Sahayak Roster.

PRAGMA foreign_keys = ON;

-- 1. Digital Breathalyzer Register (Module F1)
CREATE TABLE IF NOT EXISTS breathalyzer_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id TEXT NOT NULL,
  staff_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('loco_pilot', 'alp', 'guard', 'station_master', 'shunter')),
  train_no TEXT,
  duty_type TEXT NOT NULL CHECK(duty_type IN ('SIGN_ON', 'SIGN_OFF', 'SURPRISE_CHECK')),
  reading_mg_100ml REAL NOT NULL DEFAULT 0.0,
  passed INTEGER NOT NULL DEFAULT 1,
  verified_by TEXT NOT NULL,
  test_time TEXT NOT NULL,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ba_staff ON breathalyzer_tests(staff_id, test_time);

-- 2. Crew Rosters & Hours of Attendance (HOA) Tracking (Module F2)
CREATE TABLE IF NOT EXISTS crew_rosters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id TEXT NOT NULL,
  staff_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('loco_pilot', 'alp', 'guard')),
  train_no TEXT NOT NULL,
  station_code TEXT NOT NULL,
  sign_on_time TEXT NOT NULL,
  sign_off_time TEXT,
  duty_hours_limit REAL NOT NULL DEFAULT 10.0,
  consecutive_night_shifts INTEGER NOT NULL DEFAULT 0,
  rest_hours_due REAL NOT NULL DEFAULT 16.0,
  status TEXT NOT NULL DEFAULT 'ON_DUTY' CHECK(status IN ('ON_DUTY', 'RESTING', 'BREACH_WARNING', 'COMPLETED')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crew_stn_status ON crew_rosters(station_code, status);

-- 3. Station Staff Shift Scheduler (Module F3)
CREATE TABLE IF NOT EXISTS staff_shifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id TEXT NOT NULL,
  staff_name TEXT NOT NULL,
  role_id TEXT NOT NULL,
  station_code TEXT NOT NULL,
  shift_date TEXT NOT NULL,
  shift_type TEXT NOT NULL CHECK(shift_type IN ('morning', 'afternoon', 'night')),
  attendance_status TEXT NOT NULL DEFAULT 'PRESENT' CHECK(attendance_status IN ('PRESENT', 'ABSENT', 'LEAVE', 'REST')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shifts_stn_date ON staff_shifts(station_code, shift_date);

-- 4. Sahayak (Licensed Porter) Roster (Module F4)
CREATE TABLE IF NOT EXISTS sahayak_roster (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  badge_number TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  station_code TEXT NOT NULL,
  assigned_platform INTEGER NOT NULL DEFAULT 1,
  shift TEXT NOT NULL DEFAULT 'morning' CHECK(shift IN ('morning', 'afternoon', 'night')),
  on_duty INTEGER NOT NULL DEFAULT 1,
  tariff_fixed_inr REAL NOT NULL DEFAULT 150.0,
  last_active TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sahayak_stn ON sahayak_roster(station_code, on_duty);
