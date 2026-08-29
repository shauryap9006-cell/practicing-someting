-- Migration 008: Conformal PID State Persistence (Task T6)
CREATE TABLE IF NOT EXISTS conformal_pid_state (
    group_key TEXT PRIMARY KEY,
    target_alpha REAL NOT NULL DEFAULT 0.20,
    current_alpha REAL NOT NULL DEFAULT 0.20,
    integral REAL NOT NULL DEFAULT 0.0,
    prev_error REAL NOT NULL DEFAULT 0.0,
    steps INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
