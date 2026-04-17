import collections
import json
import re
import time
from datetime import datetime, timezone

import anthropic

from scraper.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- TPM tracking (shared within this module) ---
_TPM_LIMIT = 45000
_token_window: collections.deque = collections.deque()


def _record_tokens(tokens: int):
    now = time.time()
    _token_window.append((now, tokens))
    while _token_window and _token_window[0][0] < now - 60:
        _token_window.popleft()


def _wait_for_token_budget(estimated_tokens: int):
    while True:
        now = time.time()
        while _token_window and _token_window[0][0] < now - 60:
            _token_window.popleft()
        used = sum(t for _, t in _token_window)
        if used + estimated_tokens < _TPM_LIMIT:
            return
        oldest_time = _token_window[0][0] if _token_window else now
        wait = max(oldest_time + 60 - time.time() + 1, 1)
        print(f"    Quality scorer approaching token limit ({used:,}/{_TPM_LIMIT:,} TPM) — waiting {wait:.0f}s", flush=True)
        time.sleep(wait)


SCORING_PROMPT = """You are assessing the quality of interview questions for a technical interview preparation platform.

Rate the following text on a 1–5 scale using two criteria together:
1. Is the text a complete, well-formed, directly askable question — not a title, label, fragment, or description?
2. Is it the kind of substantive question that would appear in a real technical interview at a serious tech company?

Scoring rubric:
5 — Complete, specific, directly askable as-is. A candidate handed this would immediately know what to do. Substantive and realistic for a technical interview.
4 — A real, specific question with very minor phrasing roughness. Still clearly askable and realistic.
3 — Grammatically a question, but too vague, too shallow, or too generic to be a strong interview question (e.g. "What are the log levels?", "How to clone objects?").
2 — A real topic stated as a short phrase or fragment — not yet a question (e.g. "Difference between X and Y", "Write an algorithm that does X" with no detail).
1 — Not a question at all: problem titles ("Trapping Rain Water"), topic labels, conversational fragments ("So what can we do about it?"), or descriptions of questions ("A variation of merging intervals").

Critical rules:
- Do NOT use your background knowledge to infer what a question probably means. Judge only the text as written.
- "Trapping Rain Water" is a 1 — it is a problem title, not a question.
- "What do you like about ADP?" is a 3 at best — it is not a technical interview question.
- A question must be substantive to score 4 or 5. Simple recall questions ("What is X?", "What are the log levels?") cap at 3.
- A 5 requires the question to be both well-formed AND something a serious tech interviewer would actually ask.

Respond with JSON only, no other text: {"score": <integer 1-5>}"""


def score_question(question_text: str, company: str, retries: int = 3) -> int | None:
    """
    Score a single question for realism on a 1–5 scale using Haiku.
    Returns the integer score, or None if scoring fails.
    """
    prompt = f"Company: {company}\n\nQuestion: {question_text}"
    estimated = len(prompt) // 4

    _wait_for_token_budget(estimated)
    time.sleep(1.3)  # Tier 1 RPM cap: 50 req/min = 1 req per 1.2s

    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=64,
                system=SCORING_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            _record_tokens(response.usage.input_tokens)

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```[a-z]*\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)
            result = json.loads(raw)
            score = int(result["score"])
            if 1 <= score <= 5:
                return score
            return None

        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback: extract score with regex in case of extra text
            match = re.search(r'"score"\s*:\s*([1-5])', raw)
            if match:
                return int(match.group(1))
            return None
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"    Rate limit hit — waiting {wait}s (attempt {attempt + 1}/{retries})", flush=True)
            time.sleep(wait)
        except anthropic.APIConnectionError:
            wait = 10 * (attempt + 1)
            print(f"    Connection error — waiting {wait}s (attempt {attempt + 1}/{retries})", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"    Quality scoring failed: {e}", flush=True)
            return None

    return None


def score_batch(conn, batch_size: int = 50):
    """
    Score all questions in the DB that don't yet have a quality_score.
    Updates quality_score and quality_assessed_at in place.
    Prints progress as it runs.
    """
    rows = conn.execute(
        "SELECT id, question_text, company FROM questions WHERE quality_score IS NULL"
    ).fetchall()

    total = len(rows)
    if total == 0:
        print("All questions already scored.")
        return

    print(f"Scoring {total} unscored questions...", flush=True)

    for i, row in enumerate(rows, 1):
        score = score_question(row["question_text"], row["company"] or "Unknown")
        now = datetime.now(timezone.utc).isoformat()

        if score is not None:
            conn.execute(
                "UPDATE questions SET quality_score = ?, quality_assessed_at = ? WHERE id = ?",
                (score, now, row["id"])
            )
            conn.commit()

        if i % batch_size == 0 or i == total:
            print(f"  {i}/{total} scored", flush=True)

    print("Batch scoring complete.", flush=True)
