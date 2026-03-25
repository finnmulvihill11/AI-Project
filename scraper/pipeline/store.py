import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from scraper.pipeline.normalize import normalize_company

MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_migrations(db_path: str):
    """Apply any unapplied migrations in order."""
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()

    applied = {row["filename"] for row in conn.execute("SELECT filename FROM migrations")}
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        if migration_file.name not in applied:
            sql = migration_file.read_text()
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO migrations (filename, applied_at) VALUES (?, ?)",
                (migration_file.name, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            print(f"  Applied migration: {migration_file.name}")

    conn.close()


def save_question(conn: sqlite3.Connection, question: dict, canonical_id: str = None) -> str:
    """Insert a question. Returns the new question's id."""
    qid = str(uuid.uuid4())
    conn.execute("""
        INSERT OR IGNORE INTO questions
            (id, canonical_id, question_text, answer_text, company, role,
             source_url, scraped_at, source_date, content_hash, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        qid,
        canonical_id or qid,
        question["question_text"],
        question.get("answer_text"),
        normalize_company(question.get("company")),
        question.get("role"),
        question["source_url"],
        datetime.now(timezone.utc).isoformat(),
        question.get("source_date"),
        question["content_hash"],
        question.get("embedding"),
    ))
    conn.commit()
    return qid


def save_incomplete(conn: sqlite3.Connection, question: dict, canonical_id: str = None) -> str:
    """Insert a question missing company or role into the incomplete table. Returns the new id."""
    qid = str(uuid.uuid4())
    conn.execute("""
        INSERT OR IGNORE INTO incomplete
            (id, canonical_id, question_text, answer_text, company, role,
             source_url, scraped_at, source_date, content_hash, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        qid,
        canonical_id or qid,
        question["question_text"],
        question.get("answer_text"),
        normalize_company(question.get("company")),
        question.get("role"),
        question["source_url"],
        datetime.now(timezone.utc).isoformat(),
        question.get("source_date"),
        question["content_hash"],
        question.get("embedding"),
    ))
    conn.commit()
    return qid


def get_all_hashes_incomplete(conn: sqlite3.Connection) -> set:
    """Return all stored content hashes from the incomplete table."""
    rows = conn.execute("SELECT content_hash FROM incomplete").fetchall()
    return {row["content_hash"] for row in rows}


def get_all_embeddings_incomplete(conn: sqlite3.Connection) -> list:
    """Return all stored (id, canonical_id, embedding) from the incomplete table."""
    rows = conn.execute(
        "SELECT id, canonical_id, embedding FROM incomplete WHERE embedding IS NOT NULL"
    ).fetchall()
    return [dict(row) for row in rows]


def save_review(conn: sqlite3.Connection, question: dict, reasoning: str):
    """Insert an unattributable question into the review table."""
    conn.execute("""
        INSERT INTO review (id, question_text, source_url, haiku_reasoning, scraped_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        question["question_text"],
        question["source_url"],
        reasoning,
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()


def save_failed_page(conn: sqlite3.Connection, url: str, error: str):
    """Log a page that failed to load."""
    conn.execute("""
        INSERT INTO failed_pages (id, url, error, attempted_at)
        VALUES (?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        url,
        error,
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()


def touch_scraped_at(conn: sqlite3.Connection, content_hash: str):
    """Refresh scraped_at for a question seen again on re-scrape."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE questions SET scraped_at = ? WHERE content_hash = ?", (now, content_hash))
    conn.execute("UPDATE incomplete SET scraped_at = ? WHERE content_hash = ?", (now, content_hash))
    conn.commit()


def is_file_seen(conn: sqlite3.Connection, file_hash: str) -> bool:
    """Return True if this exact file content has been processed before."""
    return conn.execute(
        "SELECT 1 FROM scraped_files WHERE file_hash = ?", (file_hash,)
    ).fetchone() is not None


def mark_file_seen(conn: sqlite3.Connection, file_hash: str, url: str):
    """Record a file as processed, or update last_seen if already known."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO scraped_files (file_hash, url, first_seen, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_hash) DO UPDATE SET last_seen = excluded.last_seen
    """, (file_hash, url, now, now))
    conn.commit()


def get_all_hashes(conn: sqlite3.Connection) -> set:
    """Return all stored content hashes for exact dedup."""
    rows = conn.execute("SELECT content_hash FROM questions").fetchall()
    return {row["content_hash"] for row in rows}


def get_all_embeddings(conn: sqlite3.Connection) -> list:
    """Return all stored (id, canonical_id, embedding) for similarity dedup."""
    rows = conn.execute(
        "SELECT id, canonical_id, embedding FROM questions WHERE embedding IS NOT NULL"
    ).fetchall()
    return [dict(row) for row in rows]
