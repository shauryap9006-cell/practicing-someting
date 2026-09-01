-- RailTwin-X — Migration 011: Live Positions and Live Delay Ledger (Pipeline 07)
-- Supports real-time spatial positioning, dead-reckoning state, and causal delay attribution ledger.

PRAGMA foreign_keys = ON;

-- 1. Live Train Positions (Upsert key: train_no + run_date)
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

-- 2. Live Delay Attribution Ledger (Append-Only)
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
