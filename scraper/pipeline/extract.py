import collections
import hashlib
import json
import re
import time
import anthropic
from scraper.config import ANTHROPIC_API_KEY, CHUNK_SIZE_TOKENS
from scraper.pipeline.fetch import fetch
from scraper.pipeline.store import is_file_seen, mark_file_seen

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- Proactive TPM tracking ---
_TPM_LIMIT = 45000          # stay under Anthropic's 50k/min with a safe buffer
_MAX_CONTENT_TOKENS = 150000  # skip files larger than this before even chunking
_token_window: collections.deque = collections.deque()  # (timestamp, tokens) pairs


def _record_tokens(tokens: int):
    """Record tokens used in the rolling 60-second window."""
    now = time.time()
    _token_window.append((now, tokens))
    # Prune entries older than 60s
    while _token_window and _token_window[0][0] < now - 60:
        _token_window.popleft()


def _tokens_used_last_minute() -> int:
    now = time.time()
    while _token_window and _token_window[0][0] < now - 60:
        _token_window.popleft()
    return sum(t for _, t in _token_window)


def _wait_for_token_budget(estimated_tokens: int) -> bool:
    """
    Sleep proactively if sending this chunk would exceed the TPM limit.
    Returns False if the chunk itself exceeds the limit and should be skipped.
    """
    if estimated_tokens >= _TPM_LIMIT:
        return False  # no amount of waiting will help — skip this chunk

    while True:
        used = _tokens_used_last_minute()
        if used + estimated_tokens < _TPM_LIMIT:
            return True
        oldest_time = _token_window[0][0] if _token_window else time.time()
        wait = max(oldest_time + 60 - time.time() + 1, 1)
        print(f"    Approaching token limit ({used:,}/{_TPM_LIMIT:,} TPM) — waiting {wait:.0f}s", flush=True)
        time.sleep(wait)


SYSTEM_PROMPT = """You are extracting interview questions from raw markdown text.

Your job:
1. Identify whether this page contains interview questions OR is primarily a list of links to question sources
2. If questions: extract each one with company, role, and confidence
3. If a source list: return the URLs so they can be crawled next

Use all available context to determine company and role:
- The text itself ("Asked at Google", "Google SWE interview", "For Software Engineer roles")
- Surrounding content, section headers, repo name, and file path provided

Rules:
- Only extract real interview questions — not meta-commentary, instructions, or section headers
- A real question must be directly answerable. It is phrased as a question ("What is...?", "How would you...?"), a coding task ("Implement a function that...", "Write an algorithm to..."), a design challenge ("Design a system that..."), or a specific problem statement
- DO NOT extract: section titles, category labels, topic names, or table-of-contents entries. Examples of things to SKIP: "Linked List Questions", "Multiple Choice Section", "Arrays and Strings Problems", "Google Interview Questions", "Section 3: Trees", "Python (5 Questions)"
- If something looks like a heading or label rather than something you'd actually ask a candidate, skip it
- Assign role freely from context (e.g. "Software Engineer", "Data Scientist", "Product Manager") — null if unclear
- If confident a question belongs to a specific company, set confidence to "confirmed"
- If genuinely uncertain on company, set confidence to "uncertain" and explain in reasoning
- If the page is primarily a list of links to question sources (not inline questions), return a source_list
- If the page has neither questions nor useful source links, return an empty array []
- Never invent or paraphrase — extract questions exactly as written

Output format (JSON array only, no other text):

For questions:
[
  {
    "type": "question",
    "question_text": "exact question text here",
    "answer_text": "answer text if present, otherwise null",
    "company": "Company Name or null if uncertain",
    "role": "Job Role or null if unclear",
    "confidence": "confirmed or uncertain",
    "reasoning": "brief explanation if uncertain, otherwise null"
  }
]

For a source list:
[
  {
    "type": "source_list",
    "urls": ["https://...", "https://..."]
  }
]"""


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _chunk_by_headers(markdown: str) -> list[str]:
    """
    Split markdown into chunks by ## and ### headers.
    Merges small sections together to stay near CHUNK_SIZE_TOKENS.
    """
    sections = re.split(r'(?=^#{1,3} )', markdown, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    current_chunk = ""

    for section in sections:
        if _estimate_tokens(current_chunk + section) > CHUNK_SIZE_TOKENS:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk += "\n\n" + section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [markdown]


def _call_haiku(chunk: str, context: str, retries: int = 3) -> list[dict]:
    """
    Send one chunk to Haiku and return parsed list of question dicts.
    Proactively checks token budget before calling, retries on errors.
    """
    estimated = _estimate_tokens(chunk)
    if not _wait_for_token_budget(estimated):
        print(f"    Skipping chunk — too large for TPM limit (~{estimated:,} tokens)", flush=True)
        return []
    time.sleep(1)  # minimum gap between calls

    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Context: {context}\n\n---\n\n{chunk}"
                    }
                ]
            )

            # Record actual tokens used for proactive throttling
            _record_tokens(response.usage.input_tokens)

            raw = response.content[0].text.strip()

            # Strip markdown code fences if Haiku wrapped the JSON
            if raw.startswith("```"):
                raw = re.sub(r'^```[a-z]*\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)

            return json.loads(raw)

        except json.JSONDecodeError:
            return []
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"    Rate limit hit — waiting {wait}s before retry {attempt + 1}/{retries}", flush=True)
            time.sleep(wait)
        except anthropic.APIConnectionError:
            wait = 10 * (attempt + 1)
            print(f"    Connection error — waiting {wait}s before retry {attempt + 1}/{retries}", flush=True)
            time.sleep(wait)
        except Exception as e:
            raise RuntimeError(f"Haiku call failed: {e}")

    return []


def extract(file: dict, conn=None) -> dict:
    """
    Extract interview questions from a single file.
    Skips files that are too large for Haiku's context window.
    If conn is provided, skips files whose content is unchanged since the last scrape.
    Returns {"questions": [...], "discovered_urls": [...]}.
    """
    raw_url = file["raw_url"]
    context = f"Repo: {file['repo']}, File: {file['path']}, Company context: {file['company']}"

    # Use pre-fetched content if available (e.g. Reddit posts built during crawl)
    if file.get("content"):
        content = file["content"]
    else:
        try:
            content = fetch(raw_url)
        except ConnectionError as e:
            raise ConnectionError(f"Failed to fetch {raw_url}: {e}")

    if not content or not content.strip():
        return {"questions": [], "discovered_urls": []}

    file_hash = hashlib.sha256(content.encode()).hexdigest()

    # File-level dedup: skip entirely if content hasn't changed since last scrape
    if conn is not None and is_file_seen(conn, file_hash):
        print(f"    Skipping — file unchanged since last scrape", flush=True)
        return {"questions": [], "discovered_urls": [], "file_skipped": True}

    # Skip files that are too large to fit in Haiku's context window
    if _estimate_tokens(content) > _MAX_CONTENT_TOKENS:
        print(f"    Skipping — content too large (~{_estimate_tokens(content):,} tokens)", flush=True)
        return {"questions": [], "discovered_urls": []}

    chunks = _chunk_by_headers(content)
    questions = []
    had_errors = False

    for chunk in chunks:
        try:
            results = _call_haiku(chunk, context)
            questions.extend(results)
        except RuntimeError as e:
            print(f"    Chunk extraction failed: {e}", flush=True)
            had_errors = True

    # Attach source URL and source date to every item
    for item in questions:
        item["source_url"] = raw_url
        if file.get("source_date"):
            item["source_date"] = file["source_date"]

    extracted_questions = [
        q for q in questions
        if q.get("type") == "question" and q.get("confidence") in ("confirmed", "uncertain")
    ]
    source_lists = [
        item for item in questions
        if item.get("type") == "source_list"
    ]

    discovered_urls = []
    for sl in source_lists:
        discovered_urls.extend(sl.get("urls", []))

    # Only record the file as seen if Haiku ran without errors.
    # A failed run (e.g. no credits) must not poison the cache.
    if conn is not None and not had_errors:
        mark_file_seen(conn, file_hash, raw_url)

    return {
        "questions": extracted_questions,
        "discovered_urls": discovered_urls,
    }
