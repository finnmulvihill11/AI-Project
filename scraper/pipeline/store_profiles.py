import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROFILE_MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "profile_migrations"


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_migrations(db_path: str):
    """Apply any unapplied profile migrations in order."""
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()

    applied = {row["filename"] for row in conn.execute("SELECT filename FROM profile_migrations")}
    migration_files = sorted(PROFILE_MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        if migration_file.name not in applied:
            conn.executescript(migration_file.read_text())
            conn.execute(
                "INSERT INTO profile_migrations (filename, applied_at) VALUES (?, ?)",
                (migration_file.name, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            print(f"  Applied migration: {migration_file.name}")

    conn.close()


def save_profile(conn: sqlite3.Connection, profile: dict):
    """
    Insert or replace a company profile.
    Overwrites any existing profile for the same company.
    """
    conn.execute("""
        INSERT OR REPLACE INTO company_profiles
            (company, num_rounds, has_take_home, has_whiteboard, uses_lc_style,
             behavioral_framework, interview_tone, interview_style,
             pipeline_overview, what_they_value, posts_analyzed, source_urls, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile["company"],
        profile.get("num_rounds"),
        profile.get("has_take_home"),
        profile.get("has_whiteboard"),
        profile.get("uses_lc_style"),
        profile.get("behavioral_framework"),
        profile.get("interview_tone"),
        profile.get("interview_style"),
        profile.get("pipeline_overview"),
        profile.get("what_they_value"),
        profile.get("posts_analyzed", 0),
        json.dumps(profile.get("source_urls", [])),
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()
