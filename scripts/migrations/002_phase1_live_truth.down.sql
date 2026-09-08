-- Rollback 002: Drop Phase 1 live truth tables
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS planner_changesets;
DROP TABLE IF EXISTS shunting_moves;
DROP TABLE IF EXISTS block_status;
DROP TABLE IF EXISTS platform_assignments;
DROP TABLE IF EXISTS platform_states;
DROP TABLE IF EXISTS ad_events;
DROP TABLE IF EXISTS timetable_entries;
DROP TABLE IF EXISTS timetable_versions;
PRAGMA foreign_keys = ON;
