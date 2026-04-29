import json
import random
from database import get_connection


def select_questions(company_id: str, role_id: str, round_name: str) -> list[dict]:
    """
    Select questions for a session per the PRD algorithm:
    1. Get round config (question count, category weights, is_technical_only)
    2. Filter question pool by company + role + round + category
    3. If pool < 2x target count, augment from similar companies/roles
    4. Weighted random selection using quality_score² × category_weights
    Returns ordered list of question dicts ready for the session.
    """
    conn = get_connection()
    c = conn.cursor()

    # --- Step 1: Get round config ---
    round_row = c.execute("""
        SELECT * FROM company_rounds
        WHERE company_id = ? AND round_name = ?
    """, (company_id, round_name)).fetchone()

    if not round_row:
        conn.close()
        raise ValueError(f"No round config for company={company_id} round={round_name}")

    round_row = dict(round_row)
    count_range = json.loads(round_row["question_count_range"])
    target_count = count_range[1]  # use max of [min, max]
    is_technical_only = bool(round_row["is_technical_only"])
    category_weights = json.loads(round_row["category_weights"])

    # --- Step 2: Build category filter ---
    if is_technical_only:
        allowed_categories = ("technical", "coding", "system_design")
    else:
        allowed_categories = ("technical", "coding", "system_design", "behavioral")

    placeholders = ",".join("?" * len(allowed_categories))

    def fetch_pool(cid: str, quality_multiplier: float = 1.0) -> list[dict]:
        """Fetch active questions for a company, filtered by category."""
        rows = c.execute(f"""
            SELECT * FROM questions
            WHERE company_id = ?
              AND category IN ({placeholders})
              AND is_active = 1
              AND quality_score IS NOT NULL
        """, (cid, *allowed_categories)).fetchall()
        pool = []
        for r in rows:
            q = dict(r)
            q["_effective_quality"] = (q["quality_score"] or 0.0) * quality_multiplier
            pool.append(q)
        return pool

    # Primary pool: exact company match
    pool = fetch_pool(company_id, quality_multiplier=1.0)

    # --- Step 3: Fallback if pool < 2x target ---
    if len(pool) < target_count * 2:
        company_row = c.execute(
            "SELECT similar_companies FROM companies WHERE id = ?", (company_id,)
        ).fetchone()

        if company_row and company_row["similar_companies"]:
            similar_ids = json.loads(company_row["similar_companies"])
            existing_ids = {q["id"] for q in pool}

            for similar_id in similar_ids:
                if len(pool) >= target_count * 2:
                    break
                # Down-weight similar company questions by 0.7x so company-specific always preferred
                fallback = fetch_pool(similar_id, quality_multiplier=0.7)
                for q in fallback:
                    if q["id"] not in existing_ids:
                        pool.append(q)
                        existing_ids.add(q["id"])

    if not pool:
        conn.close()
        raise ValueError(f"No questions available for company={company_id} round={round_name}")

    conn.close()

    # --- Step 4: Weighted random selection ---
    # Weight = quality_score² × category_weight for this question's category
    # Squaring amplifies quality gap: 0.9² = 0.81, 0.5² = 0.25 (~3x preference)
    def weight(q: dict) -> float:
        cat_weight = category_weights.get(q["category"], 0.1)
        quality = q["_effective_quality"]
        return (quality ** 2) * cat_weight

    weights = [weight(q) for q in pool]
    total = sum(weights)
    if total == 0:
        # Fallback: uniform random if all weights zero
        selected = random.sample(pool, min(target_count, len(pool)))
    else:
        # Sample without replacement using weighted probabilities
        normalized = [w / total for w in weights]
        selected = []
        remaining_pool = list(range(len(pool)))
        remaining_weights = list(normalized)

        for _ in range(min(target_count, len(pool))):
            total_remaining = sum(remaining_weights)
            if total_remaining == 0:
                break
            probs = [w / total_remaining for w in remaining_weights]
            idx = random.choices(remaining_pool, weights=probs, k=1)[0]
            selected.append(pool[idx])
            pos = remaining_pool.index(idx)
            remaining_pool.pop(pos)
            remaining_weights.pop(pos)

    # Clean up internal field before returning
    for q in selected:
        q.pop("_effective_quality", None)

    return selected
