-- Rollback 003: Drop Phase 2 safety and compliance tables and indexes
DROP INDEX IF EXISTS idx_tsr_section_status;
DROP TABLE IF EXISTS level_crossings;
DROP TABLE IF EXISTS sop_runs;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS possessions;
