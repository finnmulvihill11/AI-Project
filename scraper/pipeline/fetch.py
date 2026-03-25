import re
import time
import requests
from playwright.sync_api import sync_playwright
from scraper.config import GITHUB_TOKEN, RATE_LIMIT_DEFAULT, REDDIT_USER_AGENT

# --- Rate limiter state (per domain) ---
_rate_state: dict = {}


def _get_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc


def _wait_for_rate_limit(domain: str):
    """Enforce rate limiting — wait if needed before next request."""
    state = _rate_state.get(domain, {})
    min_interval = state.get("min_interval", 1.0 / RATE_LIMIT_DEFAULT)
    last_request = state.get("last_request", 0)
    elapsed = time.time() - last_request
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)


def _update_rate_state(domain: str, headers: dict):
    """Read rate limit headers and update state for this domain."""
    state = _rate_state.setdefault(domain, {})
    state["last_request"] = time.time()

    # GitHub-style headers
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    limit = headers.get("X-RateLimit-Limit")

    if remaining is not None and reset is not None and limit is not None:
        remaining = int(remaining)
        reset = int(reset)
        limit = int(limit)
        now = time.time()
        seconds_until_reset = max(reset - now, 1)

        if remaining == 0:
            print(f"  Rate limit hit on {domain} — pausing {seconds_until_reset:.0f}s until reset")
            time.sleep(seconds_until_reset + 1)
        elif remaining < 50:
            # Slow down as we approach the limit
            state["min_interval"] = seconds_until_reset / max(remaining, 1)
        else:
            state["min_interval"] = 1.0 / RATE_LIMIT_DEFAULT
    else:
        # No rate limit headers — successful request, decay interval back toward default
        default_interval = 1.0 / RATE_LIMIT_DEFAULT
        current = state.get("min_interval", default_interval)
        if current > default_interval:
            state["min_interval"] = max(current * 0.5, default_interval)


def _handle_429(domain: str, response):
    """Learn rate limit from a 429 response and back off."""
    state = _rate_state.setdefault(domain, {})
    current_interval = state.get("min_interval", 1.0 / RATE_LIMIT_DEFAULT)
    new_interval = current_interval * 2  # double the wait time
    state["min_interval"] = new_interval
    retry_after = response.headers.get("Retry-After")
    wait = int(retry_after) if retry_after else new_interval
    print(f"  429 on {domain} — backing off to {new_interval:.1f}s/req, waiting {wait:.0f}s")
    time.sleep(wait)


def fetch_github(url: str) -> str | None:
    """
    Fetch content using the GitHub API.
    Handles rate limiting via response headers.
    Returns raw text content or None on failure.
    """
    domain = _get_domain(url)
    _wait_for_rate_limit(domain)

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        _update_rate_state(domain, response.headers)

        if response.status_code == 429:
            _handle_429(domain, response)
            return fetch_github(url)  # retry once after backoff

        if response.status_code == 200:
            return response.text

        return None

    except requests.RequestException as e:
        raise ConnectionError(f"GitHub API request failed: {e}")


def _html_to_text(html: str) -> str:
    """
    Convert raw HTML to clean plain text for extraction.
    Removes scripts, styles, and tags. Collapses whitespace.
    """
    # Remove script and style blocks entirely
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines to preserve structure
    html = re.sub(r'<(br|p|div|li|h[1-6]|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
    # Strip all remaining tags
    html = re.sub(r'<[^>]+>', '', html)
    # Decode common HTML entities
    html = html.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>') \
               .replace('&nbsp;', ' ').replace('&#39;', "'").replace('&quot;', '"')
    # Collapse excessive whitespace and blank lines
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r'[ \t]+', ' ', html)
    return html.strip()


def fetch_playwright(url: str) -> str | None:
    """
    Fetch a JS-rendered page using Playwright.
    Returns clean plain text (HTML stripped) or None on failure.
    """
    domain = _get_domain(url)
    _wait_for_rate_limit(domain)
    state = _rate_state.setdefault(domain, {})
    state["last_request"] = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(url, timeout=15000, wait_until="domcontentloaded")

            if response and response.status == 429:
                browser.close()
                _handle_429(domain, response)
                return fetch_playwright(url)  # retry once after backoff

            if response and response.status == 200:
                html = page.content()
                browser.close()
                return _html_to_text(html)

            browser.close()
            return None

    except Exception as e:
        raise ConnectionError(f"Playwright fetch failed: {e}")


def fetch_reddit(url: str) -> str | None:
    """
    Fetch Reddit JSON API content using requests.
    Reddit requires a descriptive User-Agent and tolerates ~1 req/sec without OAuth.
    """
    domain = _get_domain(url)
    _wait_for_rate_limit(domain)

    try:
        response = requests.get(url, headers={"User-Agent": REDDIT_USER_AGENT}, timeout=15)
        _update_rate_state(domain, response.headers)

        if response.status_code == 429:
            _handle_429(domain, response)
            return fetch_reddit(url)  # retry once after backoff

        if response.status_code == 200:
            return response.text

        return None

    except requests.RequestException as e:
        raise ConnectionError(f"Reddit request failed: {e}")


def fetch(url: str) -> str | None:
    """
    Universal fetch interface.
    Routes based on domain: GitHub API, Reddit JSON API, or Playwright for everything else.
    Returns page content as text, or raises ConnectionError on failure.
    """
    if "github.com" in url or "api.github.com" in url or "githubusercontent.com" in url:
        return fetch_github(url)
    if "reddit.com" in url:
        return fetch_reddit(url)
    return fetch_playwright(url)
