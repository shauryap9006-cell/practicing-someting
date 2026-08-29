-- RailTwin-X — Migration 006: Phase 5 Maintenance & Infrastructure
-- Implements tables for Rolling Stock Rakes & BPC Certificates, Fixed Assets, Work Orders, and Cleanliness Logs.

PRAGMA foreign_keys = ON;

-- 1. Rolling Stock Rake Health & BPC Register (Module G1)
CREATE TABLE IF NOT EXISTS rakes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rake_id TEXT NOT NULL UNIQUE,
  train_no TEXT,
  bpc_number TEXT NOT NULL UNIQUE,
  bpc_issue_date TEXT NOT NULL,
  bpc_valid_until TEXT NOT NULL,
  bpc_type TEXT NOT NULL CHECK(bpc_type IN ('PREMIUM', 'CC_INTENSIVE', 'END_TO_END', 'SPECIAL')),
  brake_power_percent REAL NOT NULL DEFAULT 100.0,
  air_brake_pressure_kg REAL NOT NULL DEFAULT 5.0,
  coach_count INTEGER NOT NULL DEFAULT 22,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'MAINTENANCE_DUE', 'OVERDUE', 'SICK_LINE')),
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_rakes_train ON rakes(train_no, status);

-- 2. Fixed Asset Register & Work Orders (Module G2)
CREATE TABLE IF NOT EXISTS station_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_tag TEXT NOT NULL UNIQUE,
  asset_type TEXT NOT NULL CHECK(asset_type IN ('TURNOUT', 'SIGNAL', 'OHE_SECTION', 'TRACK_CIRCUIT', 'POINT_MACHINE', 'CCTV', 'PA_SPEAKER', 'LIFT_ESCALATOR', 'WATER_HYDRANT')),
  station_code TEXT NOT NULL,
  platform_or_track TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPERATIONAL' CHECK(status IN ('OPERATIONAL', 'DEFECTIVE', 'DEGRADED', 'UNDER_MAINTENANCE')),
  last_serviced_date TEXT NOT NULL,
  next_service_due TEXT NOT NULL,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_stn_type ON station_assets(station_code, asset_type, status);

CREATE TABLE IF NOT EXISTS work_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_tag TEXT NOT NULL,
  station_code TEXT NOT NULL,
  issue_description TEXT NOT NULL,
  priority TEXT NOT NULL CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CANCELLED')),
  reported_by TEXT NOT NULL,
  assigned_to TEXT,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  resolution_notes TEXT,
  FOREIGN KEY (asset_tag) REFERENCES station_assets(asset_tag) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_work_orders_stn ON work_orders(station_code, status);

-- 3. Cleanliness & Bio-Toilet Feedback (Module G3)
CREATE TABLE IF NOT EXISTS cleaning_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  station_code TEXT NOT NULL,
  area_type TEXT NOT NULL CHECK(area_type IN ('PLATFORM', 'WAITING_HALL', 'TOILET', 'CONCOURSE', 'FOOT_OVER_BRIDGE')),
  platform_number INTEGER,
  cleaned_at TEXT NOT NULL,
  inspected_by TEXT NOT NULL,
  score_1_to_5 INTEGER NOT NULL CHECK(score_1_to_5 BETWEEN 1 AND 5),
  contractor_name TEXT NOT NULL DEFAULT 'Swachh Rail Agency',
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_clean_stn ON cleaning_logs(station_code, area_type);
