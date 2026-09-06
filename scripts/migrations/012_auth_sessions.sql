-- Rotating refresh-token sessions. Access tokens remain short-lived and stateless;
-- refresh tokens are hashed and revocable server-side.
CREATE TABLE IF NOT EXISTS auth_sessions (
  token_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  last_used_at TEXT,
  revoked_at TEXT,
  replaced_by TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at);
