-- Migration 003: Add source_date column to track when original content was published
-- Used for data freshness — cycle out questions whose source is older than N years

ALTER TABLE questions ADD COLUMN source_date TEXT;
ALTER TABLE incomplete ADD COLUMN source_date TEXT;
