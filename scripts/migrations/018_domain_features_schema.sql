-- Migration 018: Add domain features schema (WO-10)
-- Trains: loco_class and rake_type
ALTER TABLE trains ADD COLUMN loco_class TEXT DEFAULT 'WAP-7';
ALTER TABLE trains ADD COLUMN rake_type TEXT DEFAULT 'LHB';

-- Sections: gradient_pct and zone_id
ALTER TABLE sections ADD COLUMN gradient_pct REAL DEFAULT 0.0;
ALTER TABLE sections ADD COLUMN zone_id TEXT DEFAULT 'NCR';
