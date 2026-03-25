-- Migration 004: File-level dedup table
-- Tracks raw file content hashes so unchanged files are skipped on re-scrape (no Haiku call)

CREATE TABLE IF NOT EXISTS scraped_files (
    file_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
