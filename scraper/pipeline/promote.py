from scraper.pipeline.store import run_migrations, get_connection
from scraper.config import STAGING_DB, QUESTIONS_DB


def _promote_table(staging, production, table: str) -> tuple[int, int]:
    """
    Copy all rows from a staging table to the matching production table.
    Returns (promoted, skipped).
    """
    existing_hashes = {
        row["content_hash"]
        for row in production.execute(f"SELECT content_hash FROM {table}").fetchall()
    }

    rows = staging.execute(f"""
        SELECT id, canonical_id, question_text, answer_text, company, role,
               source_url, scraped_at, content_hash, embedding
        FROM {table}
    """).fetchall()

    promoted = 0
    skipped = 0

    for row in rows:
        if row["content_hash"] in existing_hashes:
            skipped += 1
            continue

        production.execute(f"""
            INSERT INTO {table}
                (id, canonical_id, question_text, answer_text, company, role,
                 source_url, scraped_at, content_hash, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"], row["canonical_id"], row["question_text"], row["answer_text"],
            row["company"], row["role"], row["source_url"], row["scraped_at"],
            row["content_hash"], row["embedding"],
        ))
        existing_hashes.add(row["content_hash"])
        promoted += 1

    return promoted, skipped


def promote(staging_path: str = STAGING_DB, questions_path: str = QUESTIONS_DB):
    """
    Copy all questions from staging.db to questions.db (both complete and incomplete tables).
    Safe to run multiple times — skips rows already in questions.db.
    Does not modify or wipe staging.db.
    """
    run_migrations(questions_path)

    staging = get_connection(staging_path)
    production = get_connection(questions_path)

    q_promoted, q_skipped = _promote_table(staging, production, "questions")
    i_promoted, i_skipped = _promote_table(staging, production, "incomplete")

    production.commit()
    staging.close()
    production.close()

    print()
    print("-" * 50)
    print("Promote complete")
    print(f"  Complete   — promoted: {q_promoted:>5}  skipped: {q_skipped:>5}  total: {q_promoted + q_skipped:>5}")
    print(f"  Incomplete — promoted: {i_promoted:>5}  skipped: {i_skipped:>5}  total: {i_promoted + i_skipped:>5}")
    print("-" * 50)


if __name__ == "__main__":
    promote()
