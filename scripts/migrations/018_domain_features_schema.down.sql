-- Rollback 018: Drop domain features columns
ALTER TABLE trains DROP COLUMN loco_class;
ALTER TABLE trains DROP COLUMN rake_type;
ALTER TABLE sections DROP COLUMN gradient_pct;
ALTER TABLE sections DROP COLUMN zone_id;
