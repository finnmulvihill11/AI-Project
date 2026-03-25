import json
import time
from datetime import datetime, timezone
from scraper.pipeline.fetch import fetch
from scraper.config import GITHUB_TOKEN, GITHUB_QUERY_TEMPLATES, REDDIT_POST_MAX_AGE_DAYS, REDDIT_QUERY_TEMPLATES

# Keywords that strongly suggest a repo is NOT interview prep
_BLOCKLIST_TERMS = [
    "china", "dictatorship", "censorship", "politics", "minecraft",
    "game", "bot", "discord", "android", "ios", "flutter", "minecraft",
    "pcl", "packet", "firmware", "driver", "kernel",
]


def _is_relevant(repo: dict, company: str) -> bool:
    """
    Quick relevance check based on repo name and description.
    Filters out clearly off-topic repos before crawling.
    """
    text = f"{repo['name']} {repo.get('description', '')}".lower()
    for term in _BLOCKLIST_TERMS:
        if term in text:
            return False
    return True


def discover_github_search(company: str, queries: list[str], min_stars: int, max_repos: int) -> list[dict]:
    """
    Search GitHub for repos matching each query in the list.
    Deduplicates by repo full_name across queries — same repo never crawled twice.
    Filters by min_stars, caps total repos at max_repos.
    Returns list of repo metadata dicts with type="github_repo".
    """
    repos = []
    seen_names: set[str] = set()
    per_page = 30  # GitHub max per page for search

    for query in queries:
        if len(repos) >= max_repos:
            break

        print(f"\n[{company}] Searching GitHub: '{query}' (min {min_stars} stars, max {max_repos} repos)")
        page = 1

        while len(repos) < max_repos:
            url = (
                f"https://api.github.com/search/repositories"
                f"?q={query.replace(' ', '+')}"
                f"&sort=stars&order=desc"
                f"&per_page={per_page}&page={page}"
            )

            try:
                content = fetch(url)
            except ConnectionError as e:
                print(f"  Search failed on page {page}: {e}")
                break

            if not content:
                break

            data = json.loads(content)
            items = data.get("items", [])

            if not items:
                break

            for repo in items:
                stars = repo["stargazers_count"]

                # Since results are sorted by stars descending,
                # once we're below min_stars we can stop this query
                if stars < min_stars:
                    print(f"  Stopping — below {min_stars} star threshold")
                    items = []  # signal to break outer loop too
                    break

                if len(repos) >= max_repos:
                    break

                full_name = repo["full_name"]
                if full_name in seen_names:
                    continue  # already queued from another query

                if not _is_relevant(repo, company):
                    print(f"  Skipping irrelevant repo: {full_name}")
                    continue

                seen_names.add(full_name)
                repos.append({
                    "type": "github_repo",
                    "name": repo["name"],
                    "full_name": full_name,
                    "url": repo["html_url"],
                    "api_url": repo["url"],
                    "stars": stars,
                    "description": repo.get("description", ""),
                    "company": company,
                    "source_date": repo.get("pushed_at", "")[:10] or None,  # "YYYY-MM-DD"
                })

            print(f"  Page {page}: {len(items)} repos scanned, {len(repos)} qualifying so far")

            if not items or len(items) < per_page:
                break  # no more pages or hit star threshold

            page += 1

    print(f"\n[{company}] Total GitHub repos to crawl: {len(repos)}")
    return repos


def discover_url_list(company: str, urls: list[str]) -> list[dict]:
    """
    Wraps a fixed list of URLs as directly-scrapable items.
    No crawling needed — each URL goes straight to extraction.
    """
    print(f"\n[{company}] URL list: {len(urls)} URLs")
    return [
        {
            "type": "url",
            "url": url,
            "raw_url": url,
            "path": url,
            "repo": "url_list",
            "company": company,
        }
        for url in urls
    ]


# Terms that strongly suggest a Reddit post is prep advice, celebration, or news — not question-sharing
_REDDIT_SKIP_TERMS = [
    "how i prepared", "how to prepare", "preparation tips", "study plan", "study guide",
    "got the offer", "got offer", "got an offer", "received offer", "finally got", "cracked",
    "passed the interview", "failed the interview", "rejected", "got rejected",
    "resources", "tips for", "advice for", " ama", "ask me anything",
    "vibe coding", "ai-aided", "surge in",
    "leetcode grind", "grinding leetcode", "months of disappointment", "messed up",
]

# At least one of these must appear for a post to be worth fetching
_REDDIT_REQUIRE_ONE = [
    "asked", "question", "round", "onsite", "on-site", "phone screen",
    "technical", "experience", "what did", "what was", "interview process",
]


def _is_question_post(title: str) -> bool:
    """Return True if the post title suggests it contains actual interview questions."""
    t = title.lower()
    if any(term in t for term in _REDDIT_SKIP_TERMS):
        return False
    return any(term in t for term in _REDDIT_REQUIRE_ONE)


def discover_reddit_search(company: str, queries: list[str], subreddits: list[str] | None = None) -> list[dict]:
    """
    Search Reddit for posts matching the query.
    Defaults to global Reddit search (all subreddits) so any company/role is covered.
    Pass subreddits=[...] to restrict to specific communities.
    Uses the public JSON API — no OAuth required.
    """
    cutoff_ts = time.time() - (REDDIT_POST_MAX_AGE_DAYS * 86400)
    items = []
    seen_ids: set[str] = set()  # dedup across queries — same post never hits Haiku twice

    if subreddits:
        search_targets = [(f"https://www.reddit.com/r/{sr}/search.json", f"r/{sr}") for sr in subreddits]
        restrict = "&restrict_sr=1"
    else:
        search_targets = [("https://www.reddit.com/search.json", "all of Reddit")]
        restrict = ""

    for query in queries:
        for base_url, label in search_targets:
            print(f"\n[{company}] Searching {label}: '{query}'", flush=True)
            after = None
            fetched = 0
            kept = 0

            while True:
                url = (
                    f"{base_url}"
                    f"?q={query.replace(' ', '+')}"
                    f"&sort=relevance&t=all&limit=100{restrict}"
                )
                if after:
                    url += f"&after={after}"

                try:
                    content = fetch(url)
                except ConnectionError as e:
                    print(f"  Search failed: {e}", flush=True)
                    break

                if not content:
                    break

                data = json.loads(content)
                posts = data.get("data", {}).get("children", [])

                if not posts:
                    break

                for post in posts:
                    fetched += 1
                    d = post.get("data", {})
                    if d.get("created_utc", 0) < cutoff_ts:
                        continue
                    title = d.get("title", "")
                    if not _is_question_post(title):
                        continue
                    post_id = d["id"]
                    if post_id in seen_ids:
                        continue  # already queued from another query
                    seen_ids.add(post_id)
                    items.append({
                        "type": "reddit_post",
                        "post_id": post_id,
                        "url": f"https://www.reddit.com{d['permalink']}",
                        "subreddit": d.get("subreddit", "unknown"),
                        "title": title,
                        "company": company,
                        "source_date": datetime.fromtimestamp(
                            d["created_utc"], tz=timezone.utc
                        ).strftime("%Y-%m-%d"),
                    })
                    kept += 1

                after = data.get("data", {}).get("after")
                if not after:
                    break  # Reddit has no more pages

            print(f"  {label}: {kept}/{fetched} posts kept after filter", flush=True)

    print(f"\n[{company}] Total Reddit posts to crawl: {len(items)}", flush=True)
    return items


def discover(source: dict) -> list[dict]:
    """
    Universal discovery interface.
    Routes to the right discovery function based on source type.
    Returns a list of items ready to be passed to crawl().
    """
    source_type = source["type"]
    company = source["company"]

    if source_type == "github_search":
        filters = source.get("filters", {})
        # Use explicit queries if provided, otherwise auto-generate from templates
        if source.get("queries"):
            queries = source["queries"]
        elif source.get("query"):
            queries = [source["query"]]
        else:
            queries = [t.format(company=company) for t in GITHUB_QUERY_TEMPLATES]
        return discover_github_search(
            company=company,
            queries=queries,
            min_stars=filters.get("min_stars", 50),
            max_repos=filters.get("max_repos", 100),
        )

    if source_type == "url_list":
        return discover_url_list(company=company, urls=source["urls"])

    if source_type == "reddit_search":
        filters = source.get("filters", {})
        # Use explicit queries if provided, otherwise auto-generate from templates
        queries = (
            source.get("queries")
            or [source["query"]]
            if source.get("query") or source.get("queries")
            else [t.format(company=company) for t in REDDIT_QUERY_TEMPLATES]
        )
        return discover_reddit_search(
            company=company,
            queries=queries,
            subreddits=filters.get("subreddits"),
        )

    raise NotImplementedError(f"Source type '{source_type}' not yet implemented")
