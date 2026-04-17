# AI Interview Prep — Scraper Pipeline

## Project Context

AI-powered mock technical interview platform. Users pick a company + role and get run through a live interview by an AI, followed by a post-interview analysis with scores.

**This repo is Finn's side: the scraper and data pipeline.**
Matthew owns the AI model side (enrichment, interview orchestration, scoring). The two pipelines connect through the database.

## Finn's Scope

```
websites → scraper → raw questions → storage (SQLite)
```

Matthew's pipeline reads from SQLite. Finn does not need to touch anything beyond storage.

## Data Contract

Every scraped record must produce at minimum:

| Field | Required | Notes |
|---|---|---|
| question_text | Yes | Raw question text |
| company | Yes | "Google", "Amazon", "Jane Street" |
| source_url | Yes | Page it came from — no exceptions |
| scraped_at | Yes | Timestamp |
| answer_text | No | Grab if available, null otherwise |
| role | No | e.g. "Software Engineer" — include if the source mentions it |

**Do not assign category** (technical / coding / system_design / behavioral) — Matthew's enrichment pipeline handles that automatically.

## Target Companies (in priority order)

1. Google — large public question bank, LeetCode-style + system design
2. Amazon — LeetCode + Leadership Principles behavioral questions
3. Jane Street — quant/functional programming, harder to source (Reddit, blogs, GitHub)

**Rule:** Start with one company, one site, end-to-end. Prove the pipeline works before expanding.

## Good Sources

- GitHub repos of interview prep lists (static HTML, easiest, generally safe to scrape)
- Reddit (r/cscareerquestions, r/leetcode, r/janestreet)
- Medium / personal blog interview experience posts
- LeetCode (company-tagged problems — check ToS)
- Glassdoor (JavaScript-heavy, requires browser automation — check ToS)

## Legal

Check robots.txt and Terms of Service for every site before scraping. Log compliance per source — Matthew needs this paper trail. GitHub repos and personal blogs are the safest starting point.

## Tech Stack (decided or TBD)

Options on the table — decision not yet made:

- **Option A** — Python + Playwright: per-site parsers, good for 2-3 sites, breaks on redesigns
- **Option B** — Python + BeautifulSoup: static sites only, fastest start
- **Option C** — TypeScript + pi-mono: agentic LLM-based, scales to 20+ sites (advisor rec)
- **Option D** — Python + Playwright + Claude Haiku extraction: agentic approach in Python

Core question: building for 2-3 sites or 20+?

## Storage

- **MVP:** SQLite, local
- **MVP2:** Postgres (Neon or Supabase) when moving to cloud

Store output organized by company so Matthew's pipeline can find it easily. Consider a manifest file listing what's been scraped and when.

## Deduplication

Two-layer approach:
1. Exact content hash for identical duplicates
2. Embedding similarity for near-duplicates across sources

## Environment

- Windows 11
- Python preferred over TypeScript

---

# Frontend

## Stack

- **Framework:** Next.js 16.2.2, TypeScript, App Router
- **Styling:** Tailwind CSS v4 — config lives in `app/globals.css` via `@theme` block, NOT `tailwind.config.js`
- **Auth:** Clerk (`@clerk/nextjs` v7) — keys in `frontend/.env.local`
- **Fonts:** Geist Sans + Geist Mono via `next/font/google`
- **Location:** `frontend/` folder in this repo

## Key conventions

- Tailwind v4: use `@theme inline { --color-* }` in globals.css for custom tokens. `bg-white`, `text-[#0a0a0a]` etc. work normally.
- Next.js 16 App Router: dynamic route params (`params`) are a `Promise` — must be `await`-ed in server components.
- Clerk v7: `SignedIn`/`SignedOut` components don't exist — use `useAuth()` hook. Sign-in/sign-up pages must be catch-all routes: `[[...rest]]/page.tsx`.
- Interview page (`/interview/*`) hides the Navbar — checked in `Navbar.tsx` via `usePathname`.

## Pages built

| Route | Status | Notes |
|---|---|---|
| `/` | Done | Hero, logo ticker, stats, how it works, CTA strip, footer |
| `/prep` | Placeholder | Company/role selection, routes to `/interview/demo-session` |
| `/interview/[sessionId]` | Placeholder | Dark UI, voice panel, code box, mock state |
| `/analysis/[sessionId]` | Mock data | Scores, feedback, CTAs |
| `/performance` | Mock data | Stats, bar chart, history table |
| `/sign-in`, `/sign-up` | Done | Clerk hosted components |
| `/about` | Done | How it works, companies, team, pricing — anchor sections |

## What's not built yet

- Stripe integration (free trial enforcement, subscription)
- Wire up Matthew's voice/interview API
- Wire up real company/role data from Finn's DB
- Vercel deployment

## Design system

- Yellow: `#f5c518` — CTAs, accents, step numbers, score highlights
- Black: `#0a0a0a` — headings, primary buttons
- White: `#ffffff` — background
- Border: `#e5e5e5`, Surface: `#f5f5f5`, Muted text: `text-neutral-500`
- Interview page only: dark background `bg-[#0a0a0a]`
