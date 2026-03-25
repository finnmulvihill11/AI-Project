# Finn — Starting Point for Scraping

Hey Finn. This doc is your starting point for working with Claude to clarify
the scraping requirements and build out a clear enough plan that an AI can
implement the scraper for you. Don't think of this as a blueprint — think of it
as the context you need to start that conversation. Read this first, then open
Claude and paste this file as your starting context.

---

## What We're Building

An AI-driven interview prep platform. Users pick a company and role, and we run
them through a mock technical interview using real questions scraped from the web.

Your job: build the pipeline that collects those questions and stores them.
Matthew's job: build the AI models that use them.

---

## Your Role in the System

```
You build:    websites → scraper → raw questions → storage
Matthew builds:          storage → AI enrichment → AI interview
```

Matthew's pipeline reads from wherever you store the data.
You don't need to worry about anything after storage.

---

## What Matthew Needs From You (The Data Contract)

Every scraped record needs at minimum:

| Field | Required | Notes |
|---|---|---|
| question_text | Yes | The raw question text |
| answer_text | No | Any answer from the source — null is fine |
| company | Yes | e.g. "Google", "Amazon", "Jane Street" |
| role | No | e.g. "Software Engineer" — include if available |
| source_url | Yes | The page it came from — no exceptions |
| scraped_at | Yes | Timestamp of when it was scraped |

**A few notes:**

- **category** (technical / system_design / behavioral) — do NOT worry about this.
  Matthew's AI pipeline will categorize every question automatically. If you want
  to take a rough pass at it, that's fine, but leave it null if you're unsure.
  Questions that are hard to categorize will be flagged or discarded by the pipeline.

- **role** — include it whenever the source mentions it, but don't force it.
  Questions with no role attached will be noted by the pipeline and weighted
  differently — they're still useful, just less targeted.

- **answer_text** — grab it if it's there, skip it if it's not. Many sources
  won't have a structured answer and that's fine.

The most important fields are **question_text**, **company**, and **source_url**.
Get those right and Matthew can work with the rest.

---

## What to Scrape First

Start with companies that have the most publicly available interview content.
Recommended starting points:

- **Google** — standard SWE, LeetCode-style problems, system design. Huge question
  bank available across Glassdoor, LeetCode, Reddit, and GitHub prep repos.
- **Amazon** — LeetCode + behavioral questions tied to Leadership Principles,
  system design. Well-documented online.
- **Jane Street** — quantitative trading firm. Very different interview style:
  OCaml, functional programming, probability, market-making problems. Harder to
  find structured sources — will likely require more creative sourcing (Reddit,
  blog posts, GitHub prep lists).

These are recommendations, not requirements. You and Matthew should align on
which companies to start with before you build anything site-specific, since
each company may require its own scraping logic.

**Start with one company, one site, end-to-end first.** Prove the pipeline works,
then expand.

Good sources to look at:
- Glassdoor interview questions (JavaScript-heavy, requires browser automation)
- LeetCode (company-tagged problems)
- Reddit (r/cscareerquestions, r/leetcode, r/janestreet)
- GitHub repos of interview prep lists (often static, easiest to scrape)
- Medium / blog posts of interview experiences

**Legal:** Check robots.txt and terms of service for every site before scraping.
Log whether each source explicitly allows or disallows it — Matthew needs this
for legal reasons. GitHub repos and personal blogs are generally safest.

---

## Michael's Recommended Architecture (from our advisor session)

Before the tech stack options, here's what our advisor Michael Isaac specifically
recommended for the scraping pipeline — this is worth understanding before you
decide your approach.

### The Agentic Scraping Idea

Michael's core insight: interview sites have wildly different structures.
LeetCode has structured problem sets. Glassdoor has user-submitted paragraphs.
Medium articles are blog prose. Reddit is threads and comments.

Writing a custom CSS selector scraper per site means writing and maintaining
50 different parsers. Every time a site redesigns, your scraper breaks.

His recommendation: build an **agent** that uses an LLM to understand the content
semantically rather than structurally. The agent gets a page and figures out
"this is a question, that's an answer" the same way a human would — by reading it.

### The Agent Design Michael Proposed

An agent with 5 tools:

| Tool | What it does |
|---|---|
| fetch_page | Loads a web page, respects robots.txt and rate limits |
| extract_qa_pairs | LLM reads the page and pulls out structured Q&A pairs |
| check_duplicate | Checks if this question already exists (hash + similarity) |
| store_qa | Writes the validated pair to the database with full provenance |
| enrich_metadata | Adds company, role, tags via structured LLM output |

The agent calls these tools in sequence for each page. No custom parser per site —
just point it at a URL and it figures out the rest.

**Trade-off Michael flagged:** LLM cost per page vs. engineering time writing
site-specific parsers. For 2-3 sites, parsers are probably faster to build.
For 10+ sites, the agent pays for itself. You need to decide where we land.

### The Toolkit He Suggested: pi-mono

Michael specifically recommended **pi-mono** (github.com/badlogic/pi-mono) by
Mario Zechner for implementing this agent. It includes:
- **pi-agent-core** — agent runtime with tool calling and state management
- **pi-ai** — unified LLM API (works with Claude, OpenAI, Gemini, etc.)
- **pi-pods** — manages GPU deployments (relevant later for Matthew's fine-tuned model)

Language: **TypeScript**. This is a consideration since you're on Windows and may
prefer Python. See tech stack options below.

### Legal Considerations Michael Flagged

This came up explicitly in our advisor session — worth taking seriously:

| Concern | What to do |
|---|---|
| robots.txt | Parse and respect it per site — log compliance |
| Terms of Service | Glassdoor and LeetCode likely prohibit scraping — check before building |
| Copyright | Q&A content is copyrightable — fair use is stronger for research, weaker for commercial use |
| Safest sources | Sites with open licenses (CC-BY), GitHub repos, personal blogs, your own generated content |

Document your legal review per source. Matthew needs this paper trail.

---

## Tech Stack Options

This is your decision. Here are the main approaches, with honest tradeoffs:

---

### Option A — Python + Playwright (straightforward, no LLM)
**Language:** Python
**What it is:** Playwright opens a real browser, loads JavaScript-heavy pages,
and lets you extract content via CSS selectors or XPath.

**Best for:** Getting started fast. Works on all the major sites (Glassdoor,
LeetCode are JavaScript-heavy and need a real browser).

**Tradeoff:** You write a custom extractor per site. Works well but breaks when
sites redesign their HTML. Scales poorly beyond a handful of sources.

**Effort:** Moderate. Python, well-documented, works on Windows.

---

### Option B — Python + BeautifulSoup + requests (simplest)
**Language:** Python
**What it is:** requests fetches raw HTML, BeautifulSoup parses it. No browser.

**Best for:** Static sites only — GitHub pages, plain HTML blogs. Won't work on
Glassdoor or LeetCode (JavaScript-rendered, returns empty pages without a browser).

**Effort:** Low. Fastest to get something working on simple sources.

---

### Option C — Agentic Scraper with pi-mono (Michael's recommendation)
**Language:** TypeScript (Node.js)
**What it is:** The agent architecture Michael described above. LLM understands
content semantically — no custom parsers per site.

**Best for:** Scaling to many sources without multiplying engineering effort.
Robust to site redesigns. The "right" long-term architecture.

**Tradeoff:** TypeScript, more complex setup, LLM cost per page (~$0.001-0.003
per page with Claude Haiku — cheap but adds up at thousands of pages).

**Effort:** Higher upfront, but adding new sites later requires no new code.

---

### Option D — Python + LLM extraction (middle ground)
**Language:** Python
**What it is:** Playwright fetches the rendered page, then an LLM (Claude Haiku)
extracts Q&A pairs as structured JSON. Same semantic power as pi-mono but in Python.

**Best for:** If you want the agentic approach but prefer Python over TypeScript.
Slightly less structured than pi-mono but achieves the same result.

**Effort:** Moderate. Best of both worlds if TypeScript isn't comfortable.

---

### How to Think About This Decision

The core question is: **are we building for 2-3 sites or for 20+ sites?**

- If 2-3 sites (our current plan): Option A or D gets you there faster.
- If we know we'll expand quickly: Option C or D is worth the upfront investment.

Also consider: **are you comfortable with TypeScript?** Pi-mono is powerful but
if TypeScript slows you down, Python + LLM extraction (Option D) achieves the
same architecture in a language you know.

Bring this question to Claude — it can help you think through which option
fits where we are right now.

---

## Storage

Store the output somewhere both you and Matthew can access it. A shared location
in the GitHub repo is the simplest starting point — no extra infrastructure needed.
Think about how to organize it by company and source so it's easy for Matthew's
pipeline to know where to look.

Repo: **AI-Project** (Matthew has access, he can add you)

---

## How to Work with Claude on This

Open a new Claude conversation and paste this file as your starting context.
Your goal in that conversation is not to start writing code — it's to work with
Claude to get clear enough on every decision and requirement that Claude can
implement the full scraper for you in a step-by-step plan.

Use Claude to work through:
- Which site to start with and why
- Which tech stack makes the most sense for your situation
- What the full pipeline looks like from scrape to storage
- Any open questions or edge cases (legal, deduplication, error handling)

The output of that conversation should be a clear PRD for the scraping pipeline —
detailed enough that you can hand it back to Claude and say "now build this."
That's the same process Matthew is running on the AI model side. Once both PRDs
are done, we combine them and build the whole thing together.

---

## Questions to Work Through With Claude

These are the open decisions that need to be in your PRD. Claude will help you
think through each one — don't try to answer them all yourself upfront.

**Architecture:**
- Traditional scraper (per-site parsers) or agentic (LLM reads any page)?
- If agentic: pi-mono in TypeScript, or Python + LLM extraction?
- How does the agent handle a page that has no questions on it?
- What happens when extraction fails or returns garbage?

**Sources and legal:**
- Which site do we start with given legal risk vs. availability of data?
- How do we log robots.txt and ToS compliance per source?
- What's our approach to content that's clearly copyrighted?

**Deduplication:**
- How do we detect near-duplicate questions across different sources?
- Simple content hash, or embedding similarity, or both?

**Scale and reliability:**
- What happens if a scrape run gets blocked mid-way?
- Do we need rate limiting per site? How aggressive?
- How do we know when a site's HTML has changed and our extractor is broken?

**Storage and handoff:**
- What does the folder/file structure look like so Matthew's pipeline can find things?
- JSONL files per company, per source, or all in one?
- Should there be a manifest file listing what's been scraped and when?

## Before Writing Any Code — Sync with Matthew On:
1. Which companies to target first (current recommendation: Google, Amazon, Jane Street)
2. Which site to start with
3. Storage structure in the shared repo so both pipelines can connect
