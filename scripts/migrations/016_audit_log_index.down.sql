-- Rollback 016: Drop prev_hash unique index from audit_log
DROP INDEX IF EXISTS idx_audit_prev;
