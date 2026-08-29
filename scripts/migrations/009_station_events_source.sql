-- Migration 009: Tag station_events source for synthetic domain randomization tracking (Task T9 / Invariant I4)
ALTER TABLE station_events ADD COLUMN source TEXT NOT NULL DEFAULT 'observed';
