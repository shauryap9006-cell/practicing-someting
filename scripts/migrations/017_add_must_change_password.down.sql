-- Rollback 017: Remove must_change_password column from users table
ALTER TABLE users DROP COLUMN must_change_password;
