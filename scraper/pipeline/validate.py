import pickle
import random
from scraper.pipeline.store import get_connection
from scraper.pipeline.dedup import cosine_similarity
from scraper.config import STAGING_DB, SIMILARITY_THRESHOLD, BORDERLINE_LOWER


def get_chains(conn) -> list[dict]:
    """
    Return all canonical questions with their variants grouped together.
    """
    # Get all canonical questions (those that point to themselves)
    canonicals = conn.execute("""
        SELECT id, question_text, company, role, source_url
        FROM questions
        WHERE id = canonical_id
    """).fetchall()

    chains = []
    for canon in canonicals:
        variants = conn.execute("""
            SELECT id, question_text, company, role, embedding, source_url
            FROM questions
            WHERE canonical_id = ? AND id != ?
        """, (canon["id"], canon["id"])).fetchall()

        chains.append({
            "canonical_id": canon["id"],
            "canonical_text": canon["question_text"],
            "company": canon["company"],
            "role": canon["role"],
            "variants": [dict(v) for v in variants],
        })

    return chains


def score_chain(chain: dict, canon_embedding: bytes) -> list[tuple[str, float]]:
    """Return (variant_text, similarity_score) pairs for a chain."""
    if not chain["variants"]:
        return []

    canon_vector = pickle.loads(canon_embedding)
    scored = []
    for v in chain["variants"]:
        if v["embedding"]:
            variant_vector = pickle.loads(v["embedding"])
            score = cosine_similarity(canon_vector, variant_vector)
            scored.append((v["question_text"], score))
    return scored


def get_borderline_questions(conn) -> list[dict]:
    """
    Find questions whose similarity to their canonical falls in the borderline range.
    These are flagged for manual review.
    """
    all_questions = conn.execute("""
        SELECT q.id, q.question_text, q.canonical_id, q.embedding, q.company, q.role,
               c.question_text as canonical_text, c.embedding as canonical_embedding
        FROM questions q
        JOIN questions c ON q.canonical_id = c.id
        WHERE q.id != q.canonical_id
          AND q.embedding IS NOT NULL
          AND c.embedding IS NOT NULL
    """).fetchall()

    borderline = []
    for row in all_questions:
        q_vector = pickle.loads(row["embedding"])
        c_vector = pickle.loads(row["canonical_embedding"])
        score = cosine_similarity(q_vector, c_vector)
        if BORDERLINE_LOWER <= score < SIMILARITY_THRESHOLD:
            borderline.append({
                "question_text": row["question_text"],
                "canonical_text": row["canonical_text"],
                "score": score,
                "company": row["company"],
                "role": row["role"],
            })

    return borderline


def get_role_distribution(conn) -> dict:
    """Return count of questions per role."""
    rows = conn.execute("""
        SELECT role, COUNT(*) as count
        FROM questions
        GROUP BY role
        ORDER BY count DESC
    """).fetchall()
    return {row["role"] or "unknown": row["count"] for row in rows}


def run_validation(db_path: str = STAGING_DB):
    """
    Run full validation report on the staging database.
    Prints chain quality samples, borderline flags, role distribution, and summary stats.
    """
    conn = get_connection(db_path)

    # --- Stats ---
    total_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    total_incomplete = conn.execute("SELECT COUNT(*) FROM incomplete").fetchone()[0]
    incomplete_company_only = conn.execute(
        "SELECT COUNT(*) FROM incomplete WHERE company IS NOT NULL AND role IS NULL"
    ).fetchone()[0]
    incomplete_role_only = conn.execute(
        "SELECT COUNT(*) FROM incomplete WHERE company IS NULL AND role IS NOT NULL"
    ).fetchone()[0]
    total_review = conn.execute("SELECT COUNT(*) FROM review").fetchone()[0]
    total_failed = conn.execute("SELECT COUNT(*) FROM failed_pages").fetchone()[0]
    chains = get_chains(conn)
    chains_with_variants = [c for c in chains if c["variants"]]
    total_variants = sum(len(c["variants"]) for c in chains)

    print()
    print("-" * 50)
    print("Validation Report — Staging Database")
    print("-" * 50)

    # --- Chain quality samples ---
    print()
    print("CHAIN QUALITY SAMPLES")
    sample_chains = random.sample(chains_with_variants, min(5, len(chains_with_variants)))

    for chain in sample_chains:
        canon_row = conn.execute(
            "SELECT embedding FROM questions WHERE id = ?", (chain["canonical_id"],)
        ).fetchone()

        if not canon_row or not canon_row["embedding"]:
            continue

        scores = score_chain(chain, canon_row["embedding"])
        avg_score = sum(s for _, s in scores) / len(scores) if scores else 0
        flag = "! BORDERLINE" if avg_score < SIMILARITY_THRESHOLD else "OK"

        print(f"\n  Chain ({len(chain['variants'])} variant(s), avg similarity: {avg_score:.2f}) {flag}")
        print(f"  CANONICAL: \"{chain['canonical_text'][:80]}\"")
        for text, score in scores[:3]:
            print(f"  VARIANT:   \"{text[:80]}\" ({score:.2f})")

    if not chains_with_variants:
        print("  No chains with variants found yet.")

    # --- Borderline flags ---
    borderline = get_borderline_questions(conn)
    print()
    print(f"BORDERLINE FLAGS (similarity {BORDERLINE_LOWER}–{SIMILARITY_THRESHOLD}) — {len(borderline)} found")
    for b in borderline[:5]:
        print(f"  Score {b['score']:.2f} | CANONICAL: \"{b['canonical_text'][:60]}\"")
        print(f"           VARIANT:   \"{b['question_text'][:60]}\"")

    # --- Role distribution ---
    role_dist = get_role_distribution(conn)
    print()
    print("ROLE DISTRIBUTION")
    for role, count in list(role_dist.items())[:10]:
        print(f"  {role:<35} {count} questions")

    # --- Summary ---
    print()
    print("SUMMARY")
    print(f"  Complete questions:   {total_questions}  (company + role)")
    print(f"  Incomplete questions: {total_incomplete}  ({incomplete_company_only} company-only, {incomplete_role_only} role-only)")
    print(f"  Chains formed:        {len(chains_with_variants)}")
    print(f"  Variants linked:      {total_variants}")
    print(f"  Sent to review:       {total_review}")
    print(f"  Borderline flags:     {len(borderline)}")
    print(f"  Failed pages:         {total_failed}")
    print()
    print("Run promote.py when satisfied to push to questions.db")
    print("-" * 50)

    conn.close()
