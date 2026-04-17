-- Migration 005: Quality scoring
-- Adds quality_score (1-5) and quality_assessed_at to questions table.
-- quality_score is null for questions not yet assessed.

ALTER TABLE questions ADD COLUMN quality_score INTEGER;
ALTER TABLE questions ADD COLUMN quality_assessed_at TEXT;
