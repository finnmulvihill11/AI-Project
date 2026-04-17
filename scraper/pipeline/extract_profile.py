import collections
import json
import re
import time

import anthropic

from scraper.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- TPM tracking ---
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
        print(f"    Profile extractor approaching TPM limit ({used:,}/{_TPM_LIMIT:,}) — waiting {wait:.0f}s", flush=True)
        time.sleep(wait)


def _call_haiku(system: str, user: str, max_tokens: int = 1024, retries: int = 3) -> dict | list | None:
    """Call Haiku, strip code fences, parse JSON. Returns None on failure."""
    estimated = len(user) // 4
    _wait_for_token_budget(estimated)
    time.sleep(1.3)  # Tier 1 RPM cap

    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            _record_tokens(response.usage.input_tokens)

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```[a-z]*\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)
            return json.loads(raw)

        except (json.JSONDecodeError, KeyError):
            return None
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"    Rate limit — waiting {wait}s (attempt {attempt + 1}/{retries})", flush=True)
            time.sleep(wait)
        except anthropic.APIConnectionError:
            wait = 10 * (attempt + 1)
            print(f"    Connection error — waiting {wait}s (attempt {attempt + 1}/{retries})", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"    Haiku call failed: {e}", flush=True)
            return None

    return None


_SIGNALS_SYSTEM = """You are extracting interview process signals from a Reddit post.

Extract only what is explicitly described. Use null for anything not mentioned or unclear.

Distinction: null = not mentioned. false = explicitly stated this was NOT part of the process.

Return JSON only, no other text:
{
  "num_rounds": <integer or null>,
  "has_take_home": <true/false/null>,
  "has_whiteboard": <true/false/null>,
  "uses_lc_style": <true/false/null>,
  "behavioral_framework": <"Leadership Principles"/"STAR"/"none"/"other" or null>,
  "tone_notes": "<brief observation about interviewer tone or vibe, null if not mentioned>",
  "style_notes": "<observation about how interviews were conducted, null if not mentioned>",
  "pipeline_notes": "<hiring stages described, null if not mentioned>",
  "values_notes": "<what the company seemed to look for in candidates, null if not mentioned>"
}"""


_SYNTHESIS_SYSTEM = """You are building a company interview profile based on signals extracted from multiple Reddit interview experience posts.

Synthesize the signals into a cohesive profile. For structured fields, use the most commonly reported value. For prose fields, write 2-3 sentences capturing the consensus view across posts. If signals conflict, reflect the most common experience.

Return JSON only, no other text:
{
  "num_rounds": <integer — most commonly reported>,
  "has_take_home": <true/false>,
  "has_whiteboard": <true/false>,
  "uses_lc_style": <true/false>,
  "behavioral_framework": <"Leadership Principles"/"STAR"/"none" or brief description>,
  "interview_tone": "<2-3 sentences on the vibe and tone of interviews>",
  "interview_style": "<2-3 sentences on how interviews are conducted>",
  "pipeline_overview": "<2-3 sentences on the full hiring process from first contact to offer>",
  "what_they_value": "<2-3 sentences on what this company looks for in candidates>"
}"""


def extract_signals(file: dict) -> dict | None:
    """
    Extract interview process signals from a single Reddit post.
    Returns a partial profile signals dict, or None if extraction fails.
    """
    company = file.get("company", "this company")
    content = file.get("content", "")

    if not content or not content.strip():
        return None

    # Trim very long posts — we only need the first ~3000 tokens worth
    if len(content) > 12000:
        content = content[:12000]

    user = f"Company: {company}\n\nPost content:\n{content}"
    return _call_haiku(_SIGNALS_SYSTEM, user, max_tokens=512)


def synthesize_profile(company: str, signals: list[dict], source_urls: list[str]) -> dict | None:
    """
    Synthesize a list of partial signals (one per Reddit post) into a final company profile.
    Returns the complete profile dict, or None if synthesis fails.
    """
    # Filter to only non-null signals to save tokens
    clean_signals = []
    for s in signals:
        clean = {k: v for k, v in s.items() if v is not None}
        if clean:
            clean_signals.append(clean)

    if not clean_signals:
        print(f"  [{company}] No usable signals to synthesize.", flush=True)
        return None

    user = f"Company: {company}\nPosts analyzed: {len(clean_signals)}\n\nSignals:\n{json.dumps(clean_signals, indent=2)}"
    result = _call_haiku(_SYNTHESIS_SYSTEM, user, max_tokens=1024)

    if result is None:
        return None

    result["company"] = company
    result["posts_analyzed"] = len(signals)
    result["source_urls"] = source_urls
    return result
