-- Public access-request intake. Requests remain pending until an administrator
-- provisions an account through the authenticated admin workflow.
CREATE TABLE IF NOT EXISTS access_requests (
  request_id TEXT PRIMARY KEY,
  station_code TEXT NOT NULL,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  organization TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
  requested_at TEXT NOT NULL,
  reviewed_at TEXT,
  reviewed_by TEXT,
  FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_access_requests_status_time
  ON access_requests(status, requested_at);
