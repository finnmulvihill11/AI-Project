import json
from scraper.pipeline.fetch import fetch


_MAX_COMMENTS = 150  # top-scored comments only; questions are never in comment #300+


def _flatten_comments(children: list, _count: list = None) -> list[str]:
    """
    Recursively extract comment bodies from a Reddit comment tree.
    Stops after _MAX_COMMENTS total bodies collected (sorted by top score).
    Skips deleted/removed comments and 'more' pagination placeholders.
    """
    if _count is None:
        _count = [0]  # mutable counter shared across recursive calls
    texts = []
    for child in children:
        if _count[0] >= _MAX_COMMENTS:
            break
        if child.get("kind") == "more":
            continue
        data = child.get("data", {})
        body = data.get("body", "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            texts.append(body)
            _count[0] += 1
        replies = data.get("replies")
        if isinstance(replies, dict):
            nested = replies.get("data", {}).get("children", [])
            texts.extend(_flatten_comments(nested, _count))
    return texts


def _crawl_reddit_post(item: dict) -> list[dict]:
    """
    Fetch a Reddit post and all its nested comments via the public JSON API.
    Returns a single file-like dict with content pre-loaded for extraction.
    """
    url = item["url"].rstrip("/")
    json_url = f"{url}.json?limit=500&sort=top"

    try:
        content = fetch(json_url)
    except ConnectionError as e:
        print(f"    Failed to fetch Reddit post: {e}", flush=True)
        return []

    if not content:
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list) or len(data) < 2:
        return []

    post_data = data[0]["data"]["children"][0]["data"]
    title = post_data.get("title", "").strip()
    selftext = post_data.get("selftext", "").strip()

    if selftext in ("[deleted]", "[removed]"):
        selftext = ""

    comments = _flatten_comments(data[1]["data"]["children"])
    parts = [p for p in [title, selftext] + comments if p]

    if not parts:
        return []

    return [{
        "raw_url": url,
        "repo": f"reddit/r/{item['subreddit']}",
        "path": title[:100],
        "company": item["company"],
        "source_date": item.get("source_date"),
        "content": "\n\n".join(parts),
    }]


def _crawl_github_repo(repo: dict) -> list[dict]:
    """
    Crawl a GitHub repo's full file tree and return all markdown files.
    """
    full_name = repo["full_name"]
    api_url = repo["api_url"]

    try:
        repo_data = json.loads(fetch(api_url))
        default_branch = repo_data.get("default_branch", "main")
    except Exception as e:
        print(f"    Could not get repo metadata: {e}")
        return []

    tree_url = f"https://api.github.com/repos/{full_name}/git/trees/{default_branch}?recursive=1"
    try:
        content = fetch(tree_url)
    except ConnectionError as e:
        print(f"    Failed to fetch file tree: {e}")
        return []

    if not content:
        return []

    data = json.loads(content)

    if data.get("truncated"):
        print(f"    Warning: file tree truncated for {full_name} (very large repo)")

    files = []
    for item in data.get("tree", []):
        if item["type"] == "blob" and item["path"].endswith(".md"):
            raw_url = f"https://raw.githubusercontent.com/{full_name}/{default_branch}/{item['path']}"
            files.append({
                "name": item["path"].split("/")[-1],
                "path": item["path"],
                "raw_url": raw_url,
                "repo": full_name,
                "company": repo["company"],
                "source_date": repo.get("source_date"),
            })

    return files


def _crawl_url(item: dict) -> list[dict]:
    """
    A direct URL needs no crawling — return it as a single file to extract.
    """
    return [item]


def crawl(source_item: dict) -> list[dict]:
    """
    Universal crawl interface.
    Takes a discovered source item and returns a list of files ready for extraction.

    Supported item types:
      "github_repo" — crawls the GitHub repo tree for .md files
      "url"         — passes the URL straight through to extraction
    """
    item_type = source_item.get("type")

    if item_type == "github_repo":
        return _crawl_github_repo(source_item)

    if item_type == "url":
        return _crawl_url(source_item)

    if item_type == "reddit_post":
        return _crawl_reddit_post(source_item)

    raise NotImplementedError(f"Crawl not implemented for item type '{item_type}'")
