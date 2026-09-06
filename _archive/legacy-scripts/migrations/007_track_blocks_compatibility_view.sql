-- Migration 007: Add backward-compatible track_blocks view over speed_restrictions table

DROP VIEW IF EXISTS track_blocks;
CREATE VIEW IF NOT EXISTS track_blocks AS
SELECT
    id,
    from_code as from_station,
    to_code as to_station,
    from_code,
    to_code,
    speed_limit_kmph,
    cause as reason,
    cause,
    is_active,
    created_at,
    expires_at
FROM speed_restrictions;
