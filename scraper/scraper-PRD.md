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
| Company attribution | Haiku decides using cross-referencing | Folder structure is unreliable |
| Unattributable questions | Stored in review table | Don't throw away potentially good data |
| Deduplication | Exact hash + embedding similarity | Different wordings of same Q kept as variants |
| Variant storage | canonical_id chain | Variants linked to a canonical question |
| Similarity threshold | 0.90 (configurable) | Tight to start, tune in testing |
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
    → Queues each for extraction

EXTRACTION PHASE (per file)
  If file is large → chunk by markdown headers, process chunks in parallel
  If file is small → send whole file
  Claude Haiku reads content → returns structured JSON per question
    → confidence: "confirmed" | "uncertain" | "not_a_question"

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

Per chunk/file, Haiku receives the raw markdown and returns structured JSON:

```json
[
  {
    "question_text": "...",
    "answer_text": "...",
    "company": "Google",
    "confidence": "confirmed",
    "reasoning": "..."
  }
]
```

Rules given to Haiku:
- Only extract actual interview questions — not meta-commentary, instructions, or section headers
- Use cross-referencing (surrounding text, repo name, file path) to determine company
- If genuinely uncertain, set confidence to `"uncertain"` and explain in reasoning
- If the page has no questions, return empty array

Large files are chunked by markdown section headers (`##`, `###`) before sending. Chunks are processed in parallel. Results are merged before dedup.

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
