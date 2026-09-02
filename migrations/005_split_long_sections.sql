-- Migration 005: Split sections exceeding 500km into sub-sections at intermediate junctions

DELETE FROM sections WHERE (from_code='MSH' AND to_code='JNPT') OR (from_code='JNPT' AND to_code='MSH');

INSERT OR REPLACE INTO sections (from_code, to_code, distance_km, single_line, max_speed_kmph, is_dfc, loop_length_m)
VALUES ('MSH', 'BRC', 210.0, 0, 100, 1, 750),
       ('BRC', 'MSH', 210.0, 0, 100, 1, 750),
       ('BRC', 'JNPT', 302.0, 0, 100, 1, 750),
       ('JNPT', 'BRC', 302.0, 0, 100, 1, 750);
