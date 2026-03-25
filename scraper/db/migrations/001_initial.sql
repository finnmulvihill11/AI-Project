-- Migration 001: Initial schema

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    canonical_id TEXT REFERENCES questions(id),
    question_text TEXT NOT NULL,
    answer_text TEXT,
    company TEXT,
    role TEXT,
    source_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding BLOB
);

CREATE TABLE IF NOT EXISTS review (
    id TEXT PRIMARY KEY,
    question_text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    haiku_reasoning TEXT,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS failed_pages (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    error TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);

-- Indexes for fast dedup lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_hash ON questions(content_hash);
CREATE INDEX IF NOT EXISTS idx_questions_company ON questions(company);
CREATE INDEX IF NOT EXISTS idx_questions_canonical ON questions(canonical_id);
