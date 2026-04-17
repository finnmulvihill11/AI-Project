-- Migration 001: Company profiles table

CREATE TABLE IF NOT EXISTS company_profiles (
    company              TEXT PRIMARY KEY,
    num_rounds           INTEGER,
    has_take_home        INTEGER,   -- 0/1 boolean
    has_whiteboard       INTEGER,   -- 0/1 boolean
    uses_lc_style        INTEGER,   -- 0/1 boolean
    behavioral_framework TEXT,      -- e.g. "Leadership Principles", "STAR", "none"
    interview_tone       TEXT,      -- free-form prose
    interview_style      TEXT,      -- free-form prose
    pipeline_overview    TEXT,      -- free-form prose
    what_they_value      TEXT,      -- free-form prose
    posts_analyzed       INTEGER,   -- how many Reddit posts were synthesized
    source_urls          TEXT,      -- JSON array of Reddit post URLs used
    scraped_at           TEXT       -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS profile_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
