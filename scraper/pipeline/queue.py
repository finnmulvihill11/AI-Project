from urllib.parse import urlparse
from scraper.config import SCRAPABLE_DOMAINS


class CrawlQueue:
    """
    Tracks URLs to crawl and URLs already visited.
    Filters out non-scrapable domains automatically.
    """

    def __init__(self):
        self._pending: list[dict] = []
        self._visited: set[str] = set()

    def add(self, url: str, company: str, source: str = "discovered"):
        """Add a URL to the queue if it's scrapable, relevant, and not already visited."""
        url = url.strip().rstrip("/")
        if url in self._visited:
            return
        if not self._is_scrapable(url):
            return
        if not self._is_relevant_url(url):
            return
        self._visited.add(url)
        self._pending.append({"url": url, "company": company, "source": source})

    def add_many(self, urls: list[str], company: str, source: str = "discovered"):
        for url in urls:
            self.add(url, company, source)

    def pop(self) -> dict | None:
        """Return the next URL to crawl, or None if queue is empty."""
        return self._pending.pop(0) if self._pending else None

    def is_empty(self) -> bool:
        return len(self._pending) == 0

    def size(self) -> int:
        return len(self._pending)

    def _is_scrapable(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.removeprefix("www.")
            return any(domain == d or domain.endswith("." + d) for d in SCRAPABLE_DOMAINS)
        except Exception:
            return False

    def _is_relevant_url(self, url: str) -> bool:
        """
        Filter out discovered URLs that are clearly not interview content.
        Applied per-domain based on known URL patterns.
        """
        url_lower = url.lower()
        try:
            domain = urlparse(url).netloc.lower().removeprefix("www.")
        except Exception:
            return True

        # GeeksForGeeks: only follow interview experience pages
        if "geeksforgeeks.org" in domain:
            return "interview" in url_lower

        # All other allowed domains: pass through
        return True
