-- RailTwin-X SQLite Database Schema
-- SIH 2026 PS 26028 · Scope-Frozen Specification
-- All timestamps formatted as ISO strings in IST (+05:30)

PRAGMA foreign_keys = ON;

-- 1. Master Stations
CREATE TABLE IF NOT EXISTS stations (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  zone TEXT DEFAULT 'NR',
  category TEXT DEFAULT 'NSG-2',
  is_junction INT DEFAULT 0,
  platforms INT DEFAULT 2
);

-- 2. Master Trains
CREATE TABLE IF NOT EXISTS trains (
  train_no TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  class TEXT NOT NULL CHECK(class IN ('rajdhani', 'shatabdi', 'superfast', 'mail', 'passenger', 'container', 'coal_rake', 'auto_rake', 'steel_rake', 'empty_freight')),
  priority INT NOT NULL CHECK(priority BETWEEN 1 AND 5), -- 1: highest (Rajdhani/Shatabdi), 4: passenger, 5: empty freight
  trailing_tonnage REAL DEFAULT 0.0,
  is_freight INT DEFAULT 0
);

-- 3. Route Sequence per Train
CREATE TABLE IF NOT EXISTS route_stations (
  train_no TEXT NOT NULL,
  seq INT NOT NULL,
  station_code TEXT NOT NULL,
  sched_arr TEXT, -- HH:MM in IST or null for origin
  sched_dep TEXT, -- HH:MM in IST or null for destination
  halt_min INT DEFAULT 2,
  distance_km REAL NOT NULL,
  PRIMARY KEY (train_no, seq),
  FOREIGN KEY (train_no) REFERENCES trains(train_no) ON DELETE CASCADE,
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);

-- 4. Corridor Graph Edges / Block Sections
CREATE TABLE IF NOT EXISTS sections (
  from_code TEXT NOT NULL,
  to_code TEXT NOT NULL,
  distance_km REAL NOT NULL,
  single_line INT DEFAULT 0, -- 1 = single-line section (crossing holds possible), 0 = double/quad
  max_speed_kmph INT DEFAULT 130,
  is_dfc INT DEFAULT 0,
  loop_length_m INT DEFAULT 750,
  PRIMARY KEY (from_code, to_code),
  FOREIGN KEY (from_code) REFERENCES stations(code) ON DELETE RESTRICT,
  FOREIGN KEY (to_code) REFERENCES stations(code) ON DELETE RESTRICT
);

-- 5. Same-Rake Turnaround Links
CREATE TABLE IF NOT EXISTS rake_links (
  incoming_train TEXT NOT NULL,
  outgoing_train TEXT NOT NULL,
  station_code TEXT NOT NULL,
  turnaround_min INT NOT NULL DEFAULT 240, -- min required turnaround time in minutes
  PRIMARY KEY (incoming_train, outgoing_train),
  FOREIGN KEY (incoming_train) REFERENCES trains(train_no) ON DELETE CASCADE,
  FOREIGN KEY (outgoing_train) REFERENCES trains(train_no) ON DELETE CASCADE,
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);

-- 6. Historical & Collected Live Station Events (THE MOAT)
CREATE TABLE IF NOT EXISTS station_events (
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL, -- YYYY-MM-DD
  seq INT NOT NULL,
  station_code TEXT NOT NULL,
  sched_arr TEXT,
  actual_arr TEXT,
  sched_dep TEXT,
  actual_dep TEXT,
  delay_arr_min INT DEFAULT 0,
  delay_dep_min INT DEFAULT 0,
  collected_at TEXT NOT NULL, -- ISO timestamp in IST
  event_time TEXT, -- ISO timestamp in IST for point-in-time filtering
  PRIMARY KEY (train_no, run_date, seq),
  FOREIGN KEY (train_no) REFERENCES trains(train_no) ON DELETE CASCADE,
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);

-- Indexes for lightning fast feature lookup & ML snapshots
CREATE INDEX IF NOT EXISTS idx_events_lookup ON station_events(train_no, station_code, run_date);
CREATE INDEX IF NOT EXISTS idx_events_date ON station_events(run_date);
CREATE INDEX IF NOT EXISTS idx_events_train_date ON station_events(train_no, run_date);
CREATE INDEX IF NOT EXISTS idx_events_station_date ON station_events(station_code, run_date);
CREATE INDEX IF NOT EXISTS idx_events_train_event_time ON station_events(train_no, event_time);

-- 7. Weather Observations & Archives
CREATE TABLE IF NOT EXISTS weather (
  date TEXT NOT NULL, -- YYYY-MM-DD
  station_code TEXT NOT NULL,
  temp REAL,
  precip_mm REAL DEFAULT 0.0,
  humidity REAL,
  fog_flag INT DEFAULT 0, -- 1 if fog condition met
  PRIMARY KEY (date, station_code),
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);

-- 8. Mechanistic Simulator Event Ledger (The Exact Attribution Gold)
CREATE TABLE IF NOT EXISTS sim_ledger (
  run_id TEXT NOT NULL,
  sim_time TEXT NOT NULL, -- ISO timestamp in IST
  train_no TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK(event_type IN ('CROSSING_HOLD', 'TSR', 'EXT_DWELL', 'RAKE_INHERIT', 'PLATFORM_WAIT', 'EMPTY_RETURN')),
  minutes INT NOT NULL,
  cause TEXT NOT NULL,
  counterparty TEXT, -- other train or signal/resource id causing the delay
  station_code TEXT,
  FOREIGN KEY (train_no) REFERENCES trains(train_no) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ledger_run_train ON sim_ledger(run_id, train_no);

-- 9. Speed Restrictions (TSRs)
CREATE TABLE IF NOT EXISTS speed_restrictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_code TEXT NOT NULL,
  to_code TEXT NOT NULL,
  start_km REAL DEFAULT 0.0,
  end_km REAL DEFAULT 0.0,
  speed_limit_kmph INT NOT NULL,
  cause TEXT NOT NULL,
  permanent_or_temp TEXT DEFAULT 'TEMPORARY',
  effective_from TEXT DEFAULT '2026-08-01',
  effective_to TEXT,
  status TEXT DEFAULT 'ACTIVE',
  issued_by TEXT DEFAULT 'admin',
  created_at TEXT DEFAULT '2026-08-01T00:00:00Z',
  is_active INT DEFAULT 1,
  FOREIGN KEY (from_code) REFERENCES stations(code),
  FOREIGN KEY (to_code) REFERENCES stations(code)
);

-- 10. Live Ingest Stream (Append-Only Log for Phase C)
CREATE TABLE IF NOT EXISTS live_ingest_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  train_no TEXT NOT NULL,
  station_code TEXT NOT NULL,
  scheduled_time TEXT,
  actual_time TEXT,
  delay_min INT NOT NULL,
  collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_live_ingest_lookup ON live_ingest_events(train_no, station_code, collected_at);

-- 11. Brain Orchestrator Advisory Audit Log (Append-Only for Phase G6)
CREATE TABLE IF NOT EXISTS brain_advisory_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  train_no TEXT NOT NULL,
  query_timestamp TEXT NOT NULL,
  input_delay_min REAL,
  predicted_delay_min REAL,
  confidence_tier TEXT,
  checks_passed INT,
  conflicts_count INT,
  suggested_action TEXT,
  model_version TEXT,
  raw_payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_brain_audit_train ON brain_advisory_audit(train_no, query_timestamp);

-- 12. Dispatcher Advisory ACK Log (Phase 5 — Ops Hardening)
-- Records human dispatcher accept / reject decisions on brain advisories.
CREATE TABLE IF NOT EXISTS advisory_ack_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  adv_id TEXT NOT NULL,       -- advisory identifier (brain_advisory_audit.id or uuid from payload)
  decision TEXT NOT NULL CHECK(decision IN ('accepted', 'rejected')),
  dispatcher_id TEXT,         -- optional dispatcher badge / login
  comment TEXT,               -- optional free-text comment
  recorded_at TEXT NOT NULL   -- ISO timestamp in IST
);
CREATE INDEX IF NOT EXISTS idx_ack_log_adv ON advisory_ack_log(adv_id);

-- 13. Staff Registry (Phase 6 — Ops & Field Alerts)
CREATE TABLE IF NOT EXISTS staff (
  staff_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('controller', 'pointsman', 'loco_pilot', 'guard', 'shunter', 'station_master')),
  phone TEXT NOT NULL,
  station_code TEXT NOT NULL,
  pin_hash TEXT NOT NULL,
  on_duty BOOLEAN DEFAULT 1,
  FOREIGN KEY (station_code) REFERENCES stations(code) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_staff_lookup ON staff(station_code, role, on_duty);

-- 14. Notification Audit Log (Phase 6 — Multichannel Outbound & Inbound ACK)
CREATE TABLE IF NOT EXISTS notification_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id TEXT,
  event_type TEXT,
  severity TEXT,
  channel TEXT,
  status TEXT DEFAULT 'queued',
  payload TEXT,
  sent_at TEXT,
  ack_at TEXT,
  FOREIGN KEY(staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_notif_log_staff ON notification_log(staff_id);
CREATE INDEX IF NOT EXISTS idx_notif_log_sent ON notification_log(sent_at);

-- 15. Hourly Micro-Weather (Phase B1 — Telemetry & Fog Forecast)
CREATE TABLE IF NOT EXISTS weather_hourly (
  station_code TEXT NOT NULL,
  ts_ist TEXT NOT NULL,
  date TEXT NOT NULL,
  hour INTEGER NOT NULL,
  temperature_2m REAL,
  precipitation REAL,
  visibility REAL,
  wind_speed_10m REAL,
  relative_humidity_2m REAL,
  fog_flag INTEGER DEFAULT 0,
  PRIMARY KEY (station_code, ts_ist)
);
CREATE INDEX IF NOT EXISTS idx_weather_hourly_date ON weather_hourly(station_code, date);
CREATE INDEX IF NOT EXISTS idx_weather_hourly_ts ON weather_hourly(station_code, ts_ist);

-- 16. Streaming Conformal PID State (Phase 0 — Calibration State Persistence)
CREATE TABLE IF NOT EXISTS conformal_pid_state (
  group_key TEXT PRIMARY KEY,
  target_alpha REAL NOT NULL DEFAULT 0.20,
  current_alpha REAL NOT NULL DEFAULT 0.20,
  integral REAL NOT NULL DEFAULT 0.0,
  prev_error REAL NOT NULL DEFAULT 0.0,
  steps INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

-- 17. Real-Time Live Train Positions (Pipeline 07)
CREATE TABLE IF NOT EXISTS live_positions (
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  current_station_code TEXT,
  next_station_code TEXT,
  section_id TEXT,
  speed_kmh REAL DEFAULT 0.0,
  delay_minutes REAL DEFAULT 0.0,
  confidence REAL DEFAULT 1.0,
  progress_pct REAL DEFAULT 0.0,
  is_dead_reckoned INTEGER DEFAULT 0,
  source TEXT DEFAULT 'live',
  last_event_time TEXT,
  last_gps_fix TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (train_no, run_date),
  FOREIGN KEY (train_no) REFERENCES trains(train_no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_live_positions_station ON live_positions(current_station_code);
CREATE INDEX IF NOT EXISTS idx_live_positions_updated ON live_positions(updated_at);

-- 18. Live Delay Attribution Ledger (Pipeline 07)
CREATE TABLE IF NOT EXISTS live_delay_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  train_no TEXT NOT NULL,
  run_date TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  delay_change_min REAL NOT NULL,
  previous_delay_min REAL NOT NULL,
  current_delay_min REAL NOT NULL,
  primary_cause TEXT NOT NULL,
  secondary_cause TEXT,
  confidence REAL DEFAULT 1.0,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  is_exact_accounting INTEGER DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY (train_no) REFERENCES trains(train_no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_live_delay_ledger_train ON live_delay_ledger(train_no, run_date);
CREATE INDEX IF NOT EXISTS idx_live_delay_ledger_timestamp ON live_delay_ledger(timestamp);


