-- RailTwin-X — Migration 004: Phase 3 Passenger & Commercial Experience
-- Implements tables for Delay Certificates, Commercial Stalls, and Lost & Found Registry.

PRAGMA foreign_keys = ON;

-- 1. Delay Certificates / Travel Interruption Proof (Module E1)
CREATE TABLE IF NOT EXISTS delay_certificates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cert_no TEXT NOT NULL UNIQUE,
  pnr_no TEXT,
  train_no TEXT NOT NULL,
  train_name TEXT,
  station_code TEXT NOT NULL,
  scheduled_arr TEXT NOT NULL,
  actual_arr TEXT NOT NULL,
  delay_min INTEGER NOT NULL,
  reason TEXT NOT NULL,
  issued_to_name TEXT NOT NULL,
  issued_by TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  qr_token TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_delay_certs_train ON delay_certificates(train_no, station_code);
CREATE INDEX IF NOT EXISTS idx_delay_certs_qr ON delay_certificates(qr_token);

-- 2. Commercial Lease & Stall Directory (Module E3)
CREATE TABLE IF NOT EXISTS commercial_stalls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  stall_code TEXT NOT NULL UNIQUE,
  station_code TEXT NOT NULL,
  platform_number INTEGER NOT NULL,
  stall_type TEXT NOT NULL CHECK(stall_type IN ('CATERING', 'TEA_STALL', 'BOOKSTALL', 'ATM', 'PHARMACY', 'CLOAK_ROOM', 'EXECUTIVE_LOUNGE', 'RETAIL')),
  vendor_name TEXT NOT NULL,
  contact_phone TEXT,
  monthly_rent_inr REAL NOT NULL,
  lease_start_date TEXT NOT NULL,
  lease_expiry_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'OVERDUE', 'EXPIRED', 'TERMINATED')),
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_stalls_station ON commercial_stalls(station_code, status);

-- 3. Passenger Lost & Found Register (Module E4)
CREATE TABLE IF NOT EXISTS lost_and_found (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_type TEXT NOT NULL CHECK(item_type IN ('BAG_LUGGAGE', 'ELECTRONICS', 'WALLET_CASH', 'DOCUMENT_ID', 'CLOTHING', 'OTHER')),
  description TEXT NOT NULL,
  found_location TEXT NOT NULL,
  station_code TEXT NOT NULL,
  train_no TEXT,
  found_at TEXT NOT NULL,
  found_by_staff TEXT NOT NULL,
  custody_location TEXT NOT NULL DEFAULT 'Station Master Safe',
  status TEXT NOT NULL DEFAULT 'UNCLAIMED' CHECK(status IN ('UNCLAIMED', 'CLAIMED', 'AUCTIONED', 'DISPOSED')),
  claimant_name TEXT,
  claimant_id_proof TEXT,
  claimant_phone TEXT,
  claimed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_lost_found_stn ON lost_and_found(station_code, status);
