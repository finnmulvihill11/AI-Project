-- Migration 002: Add incomplete questions table

CREATE TABLE IF NOT EXISTS incomplete (
    id TEXT PRIMARY KEY,
    canonical_id TEXT REFERENCES incomplete(id),
    question_text TEXT NOT NULL,
    answer_text TEXT,
    company TEXT,
    role TEXT,
    source_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding BLOB
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_incomplete_hash ON incomplete(content_hash);
CREATE INDEX IF NOT EXISTS idx_incomplete_company ON incomplete(company);
CREATE INDEX IF NOT EXISTS idx_incomplete_canonical ON incomplete(canonical_id);
