# Scraper Pipeline PRD & Implementation Plan

## Context

Finn is building the data pipeline for an AI mock interview platform. The scraper collects real interview questions from the web and stores them in SQLite so Matthew's AI enrichment pipeline can consume them. The goal is to build infrastructure that works end-to-end for one company (Google) first, then can be extended to any company or source by changing config — no new pipeline code per company.

**Core design principles:**
- Universal — no logic hardcoded to a specific source or company
- Adaptable — schema changes, threshold tuning, and re-scraping are all non-destructive
- Data is never thrown away unless it's clearly garbage
- Nothing reaches Matthew's database without Finn reviewing it first

---

## Decisions Made

| Decision | Choice | Reasoning |
|---|---|---|
| Language | Python | Finn's strongest language |
| Page fetching | Universal fetch interface (GitHub API or Playwright per source) | Consistent interface, optimized per source under the hood |
| Extraction | Claude Haiku | Semantic understanding, no per-site parsers |
| URL discovery | Autonomous via source-specific search (GitHub Search API etc.) | No hardcoded URL lists — scales to any company |
| Crawl depth | All markdown files in every repo | More data = better quality filtering downstream |
| Large file handling | Chunk by markdown headers, process chunks in parallel | Complete coverage + faster runtime |
| Link following | Two-phase discovery — aggregator repos queue links for crawling | Aggregators are curated source lists, not dead ends |
| Scrapable domains | Allowlist only (GitHub, Reddit, Medium, GeeksForGeeks, personal blogs) | Skip unscrapable domains (LinkedIn, YouTube, LeetCode auth walls) |
| Company attribution | Haiku decides using cross-referencing | Folder structure is unreliable |
| Role attribution | Haiku assigns freely from content | Fixed list too rigid; validate distribution in validation stage |
| Unattributable questions | Stored in review table | Don't throw away potentially good data |
| Deduplication | Exact hash + embedding similarity | Different wordings of same Q kept as variants |
| Variant storage | canonical_id chain | Variants linked to a canonical question |
| Similarity threshold | 0.85 (configurable) | Tuned from 0.90 after testing — 0.90 was too tight |
| Extraction failure (no content) | Discard silently | Nothing to retry |
| Extraction failure (load error) | Store in failed_pages | Retry later |
| Rate limiting | Adaptive — read headers if published, learn from 429s if not | Run as fast as allowed, never guess |
| Terminal output | Live progress + end summary | Useful without adding complexity |
| Workflow | Scrape → staging.db → validate → promote → questions.db | Nothing reaches Matthew without Finn approving |
| Schema changes | Numbered migration files | Move forward without rebuilding database |
| Embeddings | Always stored raw | Re-dedup with new threshold anytime, no re-scraping |
| API keys | .env file, never committed to git | Keys never leave Finn's machine |
| Starting company | Google | Largest public question bank |
| Starting source | GitHub repos | Safest legally, no login required |
| Storage | SQLite MVP → Postgres later | Matches Matthew's stack |

---

## Architecture

```
DISCOVERY PHASE
  Source config defines search query + filters
    → GitHub Search API: "Google interview questions", min_stars=50, max_repos=100
    → Returns list of repo URLs

CRAWL PHASE (per repo)
  Universal fetch interface loads repo file tree
    → Finds all .md files
    → Queues each file for extraction

EXTRACTION PHASE (per file)  ← two possible outcomes per page
  If file is large → chunk by markdown headers, process chunks in parallel
  If file is small → send whole file
  Claude Haiku reads content → returns structured JSON:
    Outcome A — questions found:
      → confidence: "confirmed" | "uncertain"
      → company: Haiku assigns from context
      → role: Haiku assigns freely (e.g. "Software Engineer", "Data Scientist")
    Outcome B — source list found (link aggregator):
      → type: "source_list"
      → urls: [list of discovered links]
      → Scrapable URLs queued for crawling
      → Non-scrapable domains (LinkedIn, YouTube, auth-walled sites) discarded

DEDUP PHASE (per question)
  1. SHA-256 hash of question_text → check exact match in staging.db
  2. If no exact match → embed with OpenAI text-embedding-3-small
  3. Cosine similarity against existing embeddings
     → similarity >= 0.90: link as variant (canonical_id chain)
     → similarity < 0.90: new canonical question

STORAGE PHASE
  confirmed + deduplicated → staging.db questions table
  uncertain attribution   → staging.db review table
  failed page loads       → staging.db failed_pages table

VALIDATION PHASE (auto-runs after scrape)
  → Chain quality report: sample chains printed side by side with scores
  → Borderline flags: questions with similarity 0.85–0.89 flagged for review
  → Summary stats

PROMOTE PHASE (manual — Finn runs when satisfied)
  → Approved data moves from staging.db → questions.db (Matthew's database)
```

---

## Universal Fetch Interface

All fetching goes through one interface: `fetch(url) → content`. Internally it routes to the right tool:

```python
fetch(url)
  ├── github.com → GitHub API (fast, uses token, respects rate limit headers)
  └── everything else → Playwright (handles JS-rendered pages)
```

Adding a new source type = add one routing rule. Calling code never changes.

---

## Source Config

Each source defines its own search query and quality filters. No source-specific logic in the pipeline itself.

```python
SOURCES = [
    {
        "type": "github",
        "company": "Google",
        "query": "Google interview questions",
        "filters": {"min_stars": 50, "max_repos": 100}
    },
    {
        "type": "reddit",
        "company": "Google",
        "query": "Google interview experience",
        "filters": {"min_upvotes": 100, "max_posts": 50}
    }
]
```

Adding a new company = add a new entry. No new pipeline code.

---

## Database Schema

### Two databases

- **`staging.db`** — raw scrape output. Disposable — wipe and re-run freely.
- **`questions.db`** — Matthew's database. Only populated via the promote step after Finn reviews.

### `questions` table (both databases)
| Field | Type | Notes |
|---|---|---|
| id | TEXT (UUID) | Primary key |
| canonical_id | TEXT (FK → self) | Self-referencing — canonical questions point to themselves |
| question_text | TEXT | Raw question |
| answer_text | TEXT | Nullable |
| company | TEXT | e.g. "Google" — assigned by Haiku |
| role | TEXT | Nullable |
| source_url | TEXT | Required — enables targeted re-scraping |
| scraped_at | TEXT | ISO timestamp — enables targeted re-scraping |
| content_hash | TEXT | SHA-256 of question_text for exact dedup |
| embedding | BLOB | Raw vector always stored — enables re-dedup without re-scraping |

### `review` table (staging.db only)
| Field | Type | Notes |
|---|---|---|
| id | TEXT (UUID) | Primary key |
| question_text | TEXT | Raw extracted text |
| source_url | TEXT | Where it came from |
| haiku_reasoning | TEXT | Why Haiku couldn't attribute it |
| scraped_at | TEXT | Timestamp |

### `failed_pages` table (staging.db only)
| Field | Type | Notes |
|---|---|---|
| id | TEXT (UUID) | Primary key |
| url | TEXT | Page that failed |
| error | TEXT | Error message / HTTP status |
| attempted_at | TEXT | Timestamp |

---

## Schema Migrations

Schema changes use numbered migration files — never modify `schema.sql` directly after initial setup:

```
db/
├── migrations/
│   ├── 001_initial.sql
│   ├── 002_add_role_field.sql
│   └── ...
└── schema.sql   ← initial schema only
```

Running migrations is non-destructive — existing data is preserved.

---

## Rate Limiting

- **If site publishes rate limit headers** (e.g. GitHub `X-RateLimit-Remaining`, `X-RateLimit-Reset`): read after every request, pause when approaching limit
- **If no headers**: start at `RATE_LIMIT_DEFAULT` (1 req/sec), detect 429 responses, back off, record the triggering rate, apply as ceiling for remainder of run

---

## Haiku Extraction

Per chunk/file, Haiku receives the raw markdown and returns one of two JSON structures:

**Questions found:**
```json
[
  {
    "type": "question",
    "question_text": "...",
    "answer_text": "...",
    "company": "Google",
    "role": "Software Engineer",
    "confidence": "confirmed",
    "reasoning": "..."
  }
]
```

**Source list found (link aggregator):**
```json
[
  {
    "type": "source_list",
    "urls": ["https://...", "https://..."]
  }
]
```

Rules given to Haiku:
- Only extract actual interview questions — not meta-commentary, instructions, or section headers
- Use cross-referencing (surrounding text, repo name, file path) to determine company
- Assign role freely from context (e.g. "Software Engineer", "Data Scientist", "Product Manager") — null if unclear
- If the page is primarily a list of links to question sources, return a source_list instead
- If genuinely uncertain on company attribution, set confidence to `"uncertain"` and explain
- If the page has neither questions nor useful links, return empty array

Large files are chunked by markdown section headers (`##`, `###`) before sending. Chunks processed in parallel, results merged before dedup.

## Scrapable Domain Allowlist

Links discovered in source lists are only followed if the domain is in the allowlist:

```python
SCRAPABLE_DOMAINS = [
    "github.com",
    "raw.githubusercontent.com",
    "reddit.com",
    "medium.com",
    "geeksforgeeks.org",
    "dev.to",
    "hackernoon.com",
]

# Never follow:
# linkedin.com, youtube.com, twitter.com, leetcode.com (auth wall),
# glassdoor.com (auth wall), indeed.com
```

---

## Validation Report (auto-runs after scrape)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validation Report — Google / GitHub
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHAIN QUALITY SAMPLES
Chain #47 (3 variants, avg similarity: 0.92)
  CANONICAL: "Reverse a linked list"
  VARIANT 1: "How would you reverse a singly linked list?" (0.93)
  VARIANT 2: "Given a linked list, reverse it in place" (0.91)
  ✓ LOOKS GOOD

Chain #83 (2 variants, avg similarity: 0.90)
  CANONICAL: "What is a hash map?"
  VARIANT 1: "Explain how a hash table works" (0.90)
  ⚠ BORDERLINE — review recommended

BORDERLINE FLAGS (similarity 0.85–0.89) — 4 found
  → See staging.db review table for full list

SUMMARY
  Questions in bank:    289
  Chains formed:        47
  Variants linked:      18
  Sent to review:       5
  Borderline flags:     4
  Failed pages:         3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run `promote.py` when satisfied to push to questions.db
```

---

## Terminal Output (during scrape)

```
[Google] Scanning repo: awesome-google-interview (repo 3/12)
  ├── README.md           → 24 questions extracted
  ├── system-design.md    → 8 questions extracted
  ├── CONTRIBUTING.md     → 0 questions (skipped)
  └── algorithms.md       → FAILED (timeout) — logged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scrape complete — Google / GitHub
  Repos scanned:        12
  Files processed:      47
  Questions extracted:  312
  Added to bank:        289
  Variants linked:      18
  Sent to review:       5
  Failed pages:         3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running validation...
```

---

## Config

```python
# config.py — all tunable values live here, never in the database

SIMILARITY_THRESHOLD = 0.90     # cosine similarity for near-duplicate detection
MAX_REPOS_PER_SOURCE = 100      # safety cap per source search
CHUNK_SIZE_TOKENS = 2000        # max tokens per Haiku chunk
GITHUB_MIN_STARS = 50           # minimum stars for GitHub repo quality filter
RATE_LIMIT_DEFAULT = 1          # req/sec default if no headers published
BORDERLINE_LOWER = 0.85         # similarity range flagged for manual review
BORDERLINE_UPPER = 0.90         # (same as SIMILARITY_THRESHOLD)
```

---

## File Structure

```
scraper/
├── scraper.ipynb          ← main entry point
├── scraper-PRD.md         ← this file
├── decisions-log.md
├── pipeline/
│   ├── discover.py        ← finds source URLs per company
│   ├── fetch.py           ← universal fetch interface (GitHub API or Playwright)
│   ├── crawl.py           ← finds all .md files in a repo
│   ├── extract.py         ← Haiku extraction, chunking, returns structured JSON
│   ├── dedup.py           ← hash + embedding similarity, canonical chain
│   ├── store.py           ← SQLite write logic (staging.db)
│   ├── validate.py        ← chain quality report, borderline flags
│   └── promote.py         ← moves approved data from staging.db → questions.db
├── db/
│   ├── schema.sql         ← initial schema
│   └── migrations/        ← numbered migration files
├── config.py              ← all tunable values
└── .env                   ← API keys (never committed)
```

---

## API Keys Required

Stored in `.env`, loaded at runtime, never committed to git:

```
GITHUB_TOKEN=...          # personal access token, public_repo scope
ANTHROPIC_API_KEY=...     # for Haiku extraction
OPENAI_API_KEY=...        # for text-embedding-3-small
```

`.env` is added to `.gitignore` before any code is written.

---

## Implementation Order

1. `.gitignore` + `.env` — keys set up before anything else
2. `schema.sql` + `store.py` — database foundation
3. `fetch.py` — universal fetch interface
4. `discover.py` — finds repo URLs for a company
5. `crawl.py` — finds all .md files in a repo
6. `extract.py` — Haiku extraction with chunking
7. `dedup.py` — hash + embedding + canonical chain
8. `validate.py` — chain quality report
9. `promote.py` — staging → production
10. Wire everything in `scraper.ipynb` with live output
11. Run end-to-end on Google, review validation report, tune if needed

---

## Long-Term Scaling Plan

### Phase 1 — Prototype (current)
Per-company queries on GitHub. One company (Google), one source. Prove the pipeline end-to-end.

### Phase 2 — Broad Scraping (post-prototype)
Switch `SOURCES` in `config.py` from per-company queries to broad source-level queries. No pipeline code changes required.

**Why:** At 100-300+ companies, per-company queries don't scale — the same repos get crawled multiple times across company queries, and maintaining per-company source configs is unmanageable. Broad queries + Haiku attribution covers everything in one pass.

**How it works:** Instead of querying `"Google interview questions"`, query `"interview questions"`, `"interview experience"`, `"system design interview"` etc. Haiku reads the content and attributes company and role from context. This is already happening accidentally — the current Google scrape pulled in 70+ companies from aggregator repos.

**Config change:**
```python
# Before (per-company)
SOURCES = [
    {"type": "github", "company": "Google", "query": "Google interview questions", ...},
    {"type": "github", "company": "Amazon", "query": "Amazon interview questions", ...},
]

# After (broad)
SOURCES = [
    {"type": "github", "query": "interview questions", "filters": {"min_stars": 50}},
    {"type": "github", "query": "interview experience", "filters": {"min_stars": 20}},
    {"type": "github", "query": "system design interview", "filters": {"min_stars": 50}},
    {"type": "reddit", "subreddit": "cscareerquestions"},
    {"type": "reddit", "subreddit": "leetcode"},
    {"type": "reddit", "subreddit": "quant"},
    ...
]
```

### Phase 3 — Incomplete Table Enrichment
After broad scraping, run a second enrichment pass on the `incomplete` table. Questions with missing company or role attribution get another attempt using:
1. Embedding similarity against confirmed questions — if a question is highly similar to a confirmed `company="Google"` question, attribute it to Google
2. Re-prompt Haiku with additional context from source URL and surrounding content

This is a separate pipeline pass, not part of the main scrape loop. Runs on-demand, non-destructive.

---

## Source List

### Tier 1 — High signal, legal, easy to scrape
| Source | Coverage | Notes |
|---|---|---|
| GitHub repos | Engineering (SWE, DS, ML, quant) | Best single source. Broad queries return curated aggregator repos. |
| Reddit | Engineering + some finance/PM | Subreddit-level more reliable than search. See subreddit list below. |
| GeeksForGeeks | Engineering | Company-tagged interview experience posts. Skews SWE but deep coverage. Static enough for BeautifulSoup. |
| Personal blogs / Medium | Mixed | High signal when found. Discovered via GitHub aggregator link-following. |
| dev.to / HackerNoon | Engineering | Lower volume but scrapable. |

### Tier 2 — High signal, legal, harder to scrape
| Source | Coverage | Notes |
|---|---|---|
| Glassdoor | Everything (all roles, all companies) | Best source for non-engineering roles. ToS prohibits scraping — requires a data partnership or legitimate API access. Do not scrape without permission. |
| Blind | Engineering + finance | ToS prohibits scraping. Same situation as Glassdoor. |
| LeetCode discuss | Engineering | Auth wall. ToS prohibits scraping. |

### Tier 3 — Locked down, do not scrape
LinkedIn, YouTube, Twitter/X, Indeed — no path to legal access.

### Reddit Subreddits
| Subreddit | Role coverage |
|---|---|
| r/cscareerquestions | SWE, general tech |
| r/leetcode | SWE, coding problems |
| r/datascience | Data Scientist, ML |
| r/MachineLearning | ML Engineer, Research |
| r/quant | Quant, finance roles |
| r/financialcareers | Finance, banking |
| r/ProductManagement | PM |
| r/UXDesign | Design |
| r/consulting | Consulting, MBB case interviews |
| r/janestreet | Jane Street specific |

### Non-Technical Role Gap
Non-technical roles (sales, marketing, operations, finance) are poorly covered by legal sources. The plan:
- **Launch:** manually seed a smaller high-quality question set for the most common non-technical roles
- **Post-launch:** user-contributed data fills the gap organically — users share their interview experiences in exchange for platform access
- **Long-term:** pursue a Glassdoor data partnership if non-technical coverage becomes a bottleneck

---

## Cost Estimates (Broad Scraping)

Rough estimates at Haiku 3 pricing ($0.25/MTok input, $1.25/MTok output). Actual cost depends heavily on discovery volume.

| Source | Calls | Input tokens | Output tokens | Est. cost |
|---|---|---|---|---|
| GitHub (broad) | ~135,000 | ~270M | ~54M | ~$135 |
| Reddit (broad) | ~50,000 | ~50M | ~10M | ~$25 |
| **Total** | | | | **~$160** |

At Haiku 3.5 pricing (~4x): **~$600**

**Cost optimization levers (implement when scaling, not now):**
- Skip files with no interview-relevant keywords before sending to Haiku
- Cache by repo commit hash — re-runs only process new/changed content (biggest win — turns $160 into ~$5-10 for incremental updates)
- Star/upvote thresholds filter low-signal sources before they hit the API
- Shorter, tighter prompts reduce input tokens on every call
- Measure actual cost-per-chunk from prototype runs before optimizing — don't guess where the waste is

---

## Adaptability Guarantees

- **Schema change** → add a migration file, existing data preserved
- **Bad scrape run** → wipe staging.db, re-run, questions.db untouched
- **Threshold was wrong** → embeddings stored raw, re-run dedup.py with new threshold, no re-scraping
- **New company** → add entry to SOURCES in config.py, no new code
- **New source type** → add routing rule to fetch.py, add entry to SOURCES
- **Haiku prompt was off** → delete by source_url + scraped_at range, re-scrape that source only

---

## Verification

- Run scraper on Google with 2-3 repos
- Check `questions` table: question_text, company, source_url correct
- Check canonical_id chain: near-duplicates linked, not duplicated
- Check `review` table: ambiguous questions present with reasoning
- Check `failed_pages`: load errors caught and logged
- Check validation report: chain samples look sensible
- Run promote.py: confirm questions.db populated correctly
- Adjust SIMILARITY_THRESHOLD in config.py, re-run dedup.py: confirm chains update without re-scraping
