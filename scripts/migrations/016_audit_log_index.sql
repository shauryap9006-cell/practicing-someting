-- Migration 016: Unique prev_hash index to prevent audit log chain forks (Fix D03)
CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_prev ON audit_log(prev_hash);
