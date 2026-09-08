-- Migration 017: Add must_change_password flag to users table (SEC-004)
ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0;
