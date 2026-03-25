# Interview App — MVP Product Requirements Document

**Version:** MVP (Demo)
**Authors:** Matthew Ivey, Finn Mulvihill
**Date:** March 2026
**Status:** Pre-implementation. This document is the source of truth for the MVP build.

---

## What the MVP Is

A locally-running AI interview simulation. No cloud hosting, no user accounts, no payment
infrastructure. The MVP is a demo — something you can run on your own machine, walk someone
through an interview, and show the full loop: company selection → live interview → post-interview
analysis. Everything needed to validate the core AI interview experience.

**What is in scope:**
- Company + role + round selection
- Live AI mock interview (audio: STT → Orchestrator → TTS)
- Pseudocode tab for coding questions (sent to orchestrator in real time)
- Post-interview analysis (4 category scores, per-question breakdown, audio replay with flags)
- Company Explorer (browse company interview metadata)
- Audio stored locally for replay
- Per-question retry

**What is explicitly out of scope (post-MVP):**
- User accounts, login, or any authentication
- Free/paid gating or subscriptions
- Cloud hosting or deployment
- Data persistence across app restarts (sessions stored locally, not permanently)
- Video avatar (audio-only)
- Behavioral interview weighting (behavioral questions exist in DB but are heavily de-weighted)
- Fine-tuning any model
- Deep audio analysis (voice scoring is transcript-based in MVP)

---

## System Architecture Overview

```
FRONTEND (React / Next.js, runs on localhost)
  │
  ├── Company Explorer Screen
  ├── Interview Selection Flow (company → role → round)
  ├── Pre-Interview Brief Screen
  ├── Waiting Room Screen
  ├── Live Interview Screen
  │     ├── Audio capture (browser MediaRecorder API — webm-opus stream)
  │     └── Pseudocode tab (coding questions only)
  ├── Analysis Loading Screen
  └── Post-Interview Analysis Screen
        └── Watch Interview Modal (audio replay + flag timeline)

  WebSocket ←──────────────────────────────────→ BACKEND

BACKEND (Python, FastAPI)
  │
  ├── WebSocket server (live interview loop)
  ├── REST endpoints (session CRUD, company/role data, analysis)
  ├── Session manager (pause/resume, state machine)
  │
  ├── Deepgram client (STT — WebSocket streaming, filler_words=true)
  ├── ElevenLabs client (TTS — streaming audio chunks)
  ├── Claude Haiku client (Orchestrator — conversational model)
  ├── Claude Sonnet client (Domain Expert — pre-session briefings + post-session scoring)
  │
  └── SQLite database (local)
```

**Backend:** Python + FastAPI. All audio processing tools (Deepgram SDK, Anthropic SDK, Silero VAD post-MVP) are Python-native. Turn detection uses Deepgram `utterance_end` — no separate VAD for MVP.

---

## Part 1: Question Engine (Data Pipeline)

> **Finn owns this entire section.** Everything in Part 1 — database schema, scraping,
> enrichment, deduplication, seeding — is your domain. Part 2 and Part 3 will consume
> whatever you build here. The only hard requirements are in **Section 1.1** (the interface
> contract): what fields must exist in the database so the live interview system can run.
> Everything else — architecture, tooling, pipeline structure, dataset size — is your call.
> Suggestions and options are provided throughout, but they are not mandates.

---

### 1.1 Interface Contract (Hard Requirements)

These are the non-negotiable outputs. Parts 2 and 3 will query these tables directly.
You can implement Act 1 however you want, but the end state must match this schema.

**`questions` table — minimum required fields:**

| Field | Type | Notes |
|---|---|---|
| id | TEXT (UUID) | Primary key |
| question_text | TEXT | Required |
| answer_text | TEXT | Nullable — grab if available |
| company_id | TEXT (FK → companies) | Required |
| role_id | TEXT (FK → roles) | Nullable |
| round | TEXT | Nullable — phone_screen, onsite_technical, etc. |
| category | TEXT | `technical` / `coding` / `system_design` / `behavioral` — assigned by enrichment |
| quality_score | REAL (0.0–1.0) | Assigned by enrichment pipeline at ingestion |
| difficulty_score | REAL (0.0–1.0) | Starts NULL — updated post-MVP from session data |
| source_url | TEXT | Required |
| scraped_at | TIMESTAMP | Required |
| tags | TEXT (JSON array) | e.g. ["binary_search", "dynamic_programming"] |
| is_active | INTEGER (bool) | Soft delete — set false for low-quality or duplicate questions |

**Category rules:**
- `coding` = question asks candidate to write code/pseudocode. "Implement binary search" = `coding`.
- `technical` = conceptual but not code. "How does binary search work?" = `technical`.
- Behavioral questions are stored normally — they'll be de-weighted at question selection time (Part 2).

**`companies` table:**
See `knowledge-base/database-design.md` for the full schema. Required fields for Act 2 to run:
`id`, `name`, `interviewer_persona`, `hint_frequency`, `hint_style`, `signals_wrong_answer_via`,
`says_answer_is_wrong_directly`, `modifies_problem_mid_interview`, `question_style`,
`wrong_answer_response`, `move_on_threshold`, `known_focus_areas`, `interview_style_tags`,
`similar_companies`, `coding_in_standard_rounds`.

**`company_rounds` table:**
`id`, `company_id`, `round_name`, `duration_minutes`, `question_count_range` (JSON `[min, max]`),
`focus`, `is_technical_only`, `category_weights` (JSON).

**`roles` table:**
`id`, `name`, `level` (nullable), `similar_roles` (JSON array of IDs), `tags` (JSON array).

**MVP companies to seed:** Google, Amazon, Jane Street.
Profiles already written: `knowledge-base/company-interviewer-profiles.md`. Seed these into the
database. The live interview system cannot run without them.

**`similar_companies` and `similar_roles`** are JSON arrays of IDs, ordered by similarity
(most similar first, top 10). These are used for question bank fallback when a company/role
has too few questions. Set manually at seed time — this is a one-time research job.

---

### 1.2 Scraping — Your Approach (Options)

How you scrape is entirely your decision. Three main approaches, each with different tradeoffs:

---

**Option A — Traditional scraping (Playwright + BeautifulSoup)**
- Playwright for JavaScript-rendered pages, BeautifulSoup for HTML parsing
- CSS selectors to target question/answer blocks
- More brittle per-site (selectors break when the site updates) but simpler and highly predictable
- Good starting point: Glassdoor, LeetCode discuss section, Blind

**Option B — Agentic scraping (pi-mono / pi-agent-core)**
- Use the existing pi-mono TypeScript framework with pi-agent-core for browser-based agents
- Agent navigates sites autonomously, identifies content, extracts structured data
- More adaptive across different site structures — less per-site maintenance
- Requires pi-mono setup and TypeScript familiarity. Higher initial complexity, lower per-site effort
- The original jumpoff document specifically proposed this as the architecture

**Option C — LLM extraction**
- Scrape raw HTML/text with a lightweight scraper, then pipe chunks to a small model for extraction
- Use Phi-3.5-mini self-hosted (or similar) to extract `question_text`, `answer_text`, `company`, `role`
  from raw page content
- Phi-3.5-mini is well-suited for this: high-volume batch, structured output, cheap to run
- Can pair with either A or B — the scraper gets the raw content, the LLM extracts structure

**Option D — Hybrid**
- Traditional scraper for well-structured sources (LeetCode, GitHub lists), LLM extraction for
  noisier sources (Reddit, Glassdoor), agentic scraping for sites that require navigation
- Most flexible, highest initial setup cost

**Recommended sources to start:**
- Curated GitHub question lists (highest quality signal — well-organized, maintained)
- LeetCode discuss section (company tags, round tags, community answers)
- Blind / Glassdoor (noisier but high volume)
- Reddit: r/cscareerquestions, r/leetcode
- Company engineering blogs (for system design questions)

**Priority order for MVP:**
Focus on Google and Amazon first — they have the most publicly available data.
Jane Street is a separate category (probability, OCaml, quant) with less public data —
scrape what exists but it may need more manual seeding.

---

### 1.3 Legal Considerations

Scraping public web content is a gray area. Before scraping any site at scale:

1. **Check robots.txt** — e.g., `glassdoor.com/robots.txt`. If a path is disallowed, don't scrape it.
2. **Review Terms of Service** — most sites prohibit scraping in their ToS. For MVP/demo at small scale
   this is generally low risk, but understand what you're working with. Don't scrape logged-in pages.
3. **Rate limiting** — add delays between requests. Don't hammer a site with 100 req/sec.
   Respectful scraping: 1–2 requests per second with randomized delays is standard.
4. **Copyright** — interview questions are generally not copyrightable (factual information).
   User-submitted content (forum posts, reviews) is trickier. For MVP internal use, this is fine.
   For a public product, this needs a legal review.
5. **No scraping behind auth** — only scrape public pages you can access without logging in.

---

### 1.4 Optional: Staging Table Architecture

The jumpoff document proposes a multi-stage pipeline with intermediate tables. This is a solid
architecture if you want clean separation between raw scrape data and enriched output:

**Option: Raw staging tables (then promote to final schema)**

```
raw_sources → raw_qa_pairs → enriched_examples → questions (final)
```

| Table | Purpose |
|---|---|
| `raw_sources` | Every URL scraped, with status (pending / processed / failed), raw HTML or text |
| `raw_qa_pairs` | Extracted question + answer pairs before enrichment, linked to raw_source |
| `enriched_examples` | After LLM enrichment: category, quality_score, tags assigned. Pre-dedup. |
| `questions` | Final table — deduplicated, quality-filtered, ready for the app |

**Why this is useful:**
- Re-runnable enrichment — if you change the enrichment prompt, re-enrich from `raw_qa_pairs`
  without re-scraping
- Debuggable — you can see exactly what the scraper extracted vs. what the LLM enriched
- Training data export is easier — `enriched_examples` is one query away from a JSONL export

**This is optional.** If you prefer to go directly from scrape to `questions` table, that works
fine for MVP. The staging architecture adds engineering overhead upfront but makes everything
downstream more maintainable.

---

### 1.5 Enrichment Pipeline

After raw question data is collected, an enrichment step assigns `category`, `tags`, and `quality_score`.

**What the enrichment model does (per question):**

1. **Categorize:** Assign `category` — `technical` / `coding` / `system_design` / `behavioral`
2. **Tag:** Assign `tags` array — e.g., ["dynamic_programming", "graphs", "probability"]
3. **Quality score:** Assign `quality_score` (0.0–1.0) based on:
   - Source quality (GitHub curated list > blog post > Reddit comment > anonymous Glassdoor)
   - Question clarity — specific and well-formed vs. vague or generic
   - Answer quality — detailed answer present (higher) vs. null (lower, not disqualifying)
   - Company specificity — real interview question for this company vs. generic LeetCode problem

**Model options for enrichment:**

| Option | Tradeoff |
|---|---|
| **Claude Sonnet (API)** | Highest accuracy, best judgment on ambiguous cases. Has API cost. Recommended for quality. |
| **Phi-3.5-mini (self-hosted)** | Zero API cost, runs locally on CPU. Lower accuracy on ambiguous categorization, still solid on clear cases. Original jumpoff recommended this for high-volume batch. |
| **Hybrid** | Phi-3.5-mini for categorization + tagging (high-volume, clear rules), Sonnet for quality scoring (judgment call, lower volume) |

The hard requirement is that `category` and `quality_score` are set by the time a question lands
in the `questions` table. Which model assigns them is your call.

**Prompt structure:**
Versioned prompts — store the prompt string alongside output so you can re-enrich if the prompt
changes. Even a simple `enrichment_prompt_version` field in the table is enough.

---

### 1.6 Deduplication

Near-duplicate questions should be detected and the lower-quality one deactivated.

**Recommended approach:**
1. Generate embeddings for each question text using **OpenAI text-embedding-3-small**
   (already in the tech stack for Part 2 — reuse the key)
2. Cosine similarity check against all existing questions
3. If similarity > 0.92: flag as near-duplicate. Keep the higher `quality_score` question,
   set `is_active = false` on the other.

**Alternative:** Content hash for exact duplicates (fast, catches copy-paste), then embedding
similarity for near-duplicates. Run content hash first to eliminate obvious duplicates cheaply.

**Threshold:** 0.92 is a reasonable starting point. Tune it once you have real data — if you're
seeing false positives (genuinely different questions being flagged), raise it.

---

### 1.7 Dataset Size Targets

Options from the jumpoff document — pick your target based on how much time you want to invest:

| Target | Questions | What it enables |
|---|---|---|
| **500 (minimum viable)** | ~500 questions across Google, Amazon, Jane Street | Enough to run MVP demo sessions without repetition. Low variety across sessions. |
| **2,000 (solid)** | ~2,000 questions | Enough variety for multiple sessions per company/role without feeling repetitive. Recommended MVP target. |
| **5,000+ (comprehensive)** | 5,000+ questions | High variety, better quality distribution, useful for fine-tuning later. More effort to collect. |

For an MVP demo, 500 is functional. For a product you'd hand to a real user, 2,000 is the floor.

---

### 1.8 Training Data Export (Future Fine-Tuning)

Not needed for MVP. But designing the pipeline with this in mind costs nothing now and
saves a rewrite later.

The goal: once there's enough high-quality data, fine-tune a local model (Qwen2.5-7B or similar
via Unsloth) to replace Claude Haiku as the conversational orchestrator. This cuts API costs at scale.

**Export format (JSONL):**
```json
{"messages": [
  {"role": "system", "content": "<orchestrator system prompt>"},
  {"role": "user", "content": "<candidate turn>"},
  {"role": "assistant", "content": "<interviewer turn>"}
]}
```
This is ChatML format — compatible with Unsloth SFT training directly.

**Alpaca format** (alternative, simpler, useful for instruction-following tasks):
```json
{"instruction": "<question>", "input": "<context>", "output": "<ideal answer>"}
```

**How to build this from your pipeline:**
- `enriched_examples` table → export as JSONL with instruction/output pairs
- Real session transcripts (post-MVP) → higher-quality training data than scraped answers

The jumpoff document also mentions GRPO for reasoning-based fine-tuning (reward model approach).
Not relevant for MVP — flag for the roadmap.

**GPU requirement:** Fine-tuning Qwen2.5-7B requires ~24GB VRAM. Neither Matthew nor Finn has
this currently. Options: RunPod, Lambda Labs, or MIT compute resources. Flag this — don't block
on it for MVP.

---

### 1.9 Company Profiles (Hand-Crafted, Must Be Seeded)

Company profiles are stored in the database and loaded at session start. They define the
interviewer's persona, hint behavior, and round structure. These are hand-crafted from research —
not scraped — and must be in the database before the app can run.

**Schema per company** (see `knowledge-base/database-design.md` for full field list):
```json
{
  "company": "Google",
  "interviewer_persona": "...",
  "hint_frequency": "medium",
  "hint_style": ["constraint_narrowing", "test_case_introduction", "single_word_prompt"],
  "signals_wrong_answer_via": ["introduce_failing_test_case", "narrow_constraint"],
  "says_answer_is_wrong_directly": false,
  "modifies_problem_mid_interview": false,
  "question_style": "well_defined",
  "wrong_answer_response": "...",
  "move_on_threshold": "medium",
  "interview_style_tags": ["algorithm_heavy", "system_design"],
  "similar_companies": ["<10 most similar company IDs, ordered>"],
  "known_focus_areas": ["data structures", "algorithms", "system design"]
}
```

**Round structure per company (separate `company_rounds` table):**
```json
{
  "company_id": "...",
  "round_name": "phone_screen",
  "duration_minutes": 45,
  "question_count_range": [1, 2],
  "focus": "one coding problem, data structures",
  "is_technical_only": true,
  "category_weights": {"technical": 0.3, "coding": 0.6, "system_design": 0.1, "behavioral": 0.0}
}
```

**Pre-written profiles for Google, Amazon, Jane Street** are in
`knowledge-base/company-interviewer-profiles.md`. Seed these into the database as part of setup.
The `similar_companies` lists need to be researched and set manually — one-time job.

---

## Part 2: Live Interview System

### 2.1 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Next.js |
| Backend | Python, FastAPI |
| Real-time communication | WebSocket (FastAPI WebSocket) |
| Database | SQLite (via SQLAlchemy or raw sqlite3) |
| STT | Deepgram Nova-2 (WebSocket streaming API, `filler_words=true`) |
| TTS | ElevenLabs Turbo v2 (streaming API) |
| Conversational Orchestrator | Claude Haiku (Anthropic API) |
| Domain Expert | Claude Sonnet (Anthropic API) |
| Turn detection | Deepgram `utterance_end` event (server-side — no separate VAD for MVP) |
| Audio recording | Browser MediaRecorder API (webm-opus) → two separate local files: user mic + AI TTS |
| Embeddings (dedup) | OpenAI text-embedding-3-small |

**Environment variables required:**
```
ANTHROPIC_API_KEY
DEEPGRAM_API_KEY
ELEVENLABS_API_KEY
OPENAI_API_KEY
AUDIO_STORAGE_PATH   # local directory for session audio files
DATABASE_PATH        # local SQLite file path
```

### 2.2 Database Schema

Full schema is in `knowledge-base/database-design.md`. Summary of tables:

**`companies`** — company profiles (persona, hint behavior, style tags, similar_companies)
**`company_rounds`** — round structure per company (duration, question count, category weights)
**`roles`** — general role types (Software Engineer, Data Scientist, etc.) with similar_roles links
**`questions`** — question bank (text, category, quality_score, difficulty_score, tags)
**`sessions`** — completed and in-progress interview sessions (see below)
**`question_feedback`** — post-MVP, user thumbs up/down on questions

**Sessions table — key fields:**
```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  company_id TEXT,
  role_id TEXT,
  round TEXT,
  status TEXT,              -- 'in_progress' | 'paused' | 'completed' | 'abandoned'
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  paused_at_question INT,   -- index of question user paused on
  question_ids TEXT,        -- JSON array, ordered
  question_briefings TEXT,  -- JSON: {question_id: briefing_object} — generated pre-session
  question_summaries TEXT,   -- JSON: {question_id: "1-3 sentence summary"} — for orchestrator context only
  question_transcripts TEXT, -- JSON: {question_id: full_turn_by_turn_transcript} — for Domain Expert scoring
  question_voice_stats TEXT, -- JSON: {question_id: {filler_count, filler_rate_per_min, wpm}} — pre-aggregated from Deepgram word data per question, passed directly to Domain Expert for Voice scoring
  pseudocode TEXT,          -- JSON: {question_id: "pseudocode text"}
  audio_path_user TEXT,      -- local path to user microphone audio file
  audio_path_ai TEXT,        -- local path to AI TTS audio file
  -- Two separate files, mixed only at replay time in the Watch Interview modal
  scores TEXT,              -- JSON: {technical_correctness, problem_solving, communication, voice}
  analysis TEXT,            -- JSON: full Domain Expert scoring output
  hints_given TEXT,         -- JSON: {question_id: hint_count} — tracked per question
  retries TEXT              -- JSON: {question_id: [{attempt_number, transcript, pseudocode, hints_given, voice_stats, analysis, audio_path, created_at}]} — all retry attempts per question, appended as they occur
);
```

### 2.3 App Navigation Structure

Two entry points from the home screen:

**Primary: Start Interview**
```
Home
└── Start Interview (button)
    └── Select Company
        └── Select Role (filtered by company — roles with data for this company)
            └── Select Round (filtered by company — rounds with data for this company)
                └── Pre-Interview Brief Screen
                    └── [Recording consent if first time]
                        └── Waiting Room
                            └── Live Interview Screen
                                └── Analysis Loading Screen
                                    └── Post-Interview Analysis Screen
```

**Secondary: Explore Companies**
```
Home
└── Explore Companies
    └── Company List
        └── Company Detail Page
            └── Round cards (name, duration, question count, focus, interviewer style)
```

### 2.4 Screen-by-Screen Specification

---

#### Screen: Home

Two buttons:
- **Start Interview** (primary CTA)
- **Explore Companies**

No other content needed for MVP.

---

#### Screen: Company Selection

List of companies with question data in the DB. For MVP: Google, Amazon, Jane Street.
Display as cards with company name and logo/icon.

---

#### Screen: Role Selection

Filtered list of roles with question data for the selected company.
Roles are general (Software Engineer, Data Scientist, HR Specialist, etc.) —
not company-specific position titles.
Only roles that have at least one active question for this company are shown.

---

#### Screen: Round Selection

List of rounds available for the selected company (from `company_rounds` table).
Each round displayed as a card:
- Round name (human-readable: "Phone Screen", "Onsite Technical", etc.)
- Duration (e.g., "45 minutes")
- Question range (e.g., "1–2 questions")
- Focus description (e.g., "Data structures and algorithms")

User selects one round and proceeds.

---

#### Screen: Pre-Interview Brief

Shown after round selection, before the waiting room.

**Contents:**
- Company name + role
- Round name
- Typical duration
- What this round typically covers (from round's `focus` field)
- Number of questions to expect

**Purpose:** Set expectations, reduce first-question shock. One screen, user reads and clicks "Begin".

**Recording consent:** If this is the user's first session, show a consent modal before
proceeding to the waiting room:
> "This session will be recorded for analysis purposes. Audio is stored locally on your
> machine. Do you consent to being recorded?"
> [Accept] [Decline — returns to home]

For MVP (no accounts), consent is captured as a local flag (localStorage or a local file).
If consent was previously given, skip the modal.

---

#### Screen: Waiting Room

**What happens server-side during this screen (pre-session processing):**

1. **Question selection** — backend runs the selection algorithm (see Section 2.6) and
   picks N questions for this session.

2. **Domain Expert briefing generation** — Claude Sonnet generates a briefing JSON for
   each selected question. All briefings are stored in the session record
   (`session.question_briefings`). This takes 5-15 seconds depending on question count.

3. **Session record created** — session written to DB with status `in_progress`.

4. **Audio recording begins** — backend signals frontend to start recording.

**What the user sees:**
- A waiting room screen ("Your interviewer is joining...")
- The AI "joins" after a randomized delay of **5–30 seconds** after briefing generation completes.
  The delay is random within that range — sometimes fast, sometimes slower. Builds anticipatory
  tension and activates real interview anxiety. This is intentional. The variability is the point.
- Once the delay expires, the WebSocket connection is established and the interview begins.

**Two states:** "Preparing your interview..." during briefing generation, then "Your interviewer will join shortly..." for the intentional 5–30s randomized delay.

---

#### Screen: Live Interview

The core product screen. Contains:

**Left panel (main):**
- Interview conversation — AI audio plays through speakers
- No transcript shown during interview (real interviews don't show transcripts)
- Microphone status indicator (recording/not recording)
- Pause button → opens pause overlay
- End Interview button (with confirmation)

**Right panel (appears only when `category = coding`):**
- Pseudocode tab — plain text area, monospace font
- Label: "Write your pseudocode here"
- No syntax highlighting required for MVP
- No submit button — content is sent to orchestrator on every user turn automatically

**Pause overlay (when Pause is clicked):**
- "Interview paused"
- Resume button → resumes exactly where left off
- End Interview button → confirms end, saves session, proceeds to analysis of completed questions

**Verbal time warning:**
The orchestrator delivers time warnings verbally, not visually:
"You have about 5 minutes left."
No visual countdown timer. This is how real interviews work.

---

#### Screen: Analysis Loading

Shown while the Domain Expert runs post-session scoring.

- "Analyzing your interview..." loading state
- Natural wait time: 1–2 minutes (Domain Expert scoring full session)
- No artificial delay added — this is the cooldown
- When analysis completes, automatically transitions to Post-Interview Analysis screen

---

#### Screen: Post-Interview Analysis

**Top section:**
Four score cards displayed horizontally:
- Technical Correctness: X.X / 10
- Problem-Solving: X.X / 10
- Communication: X.X / 10
- Voice: X.X / 10

**Watch Interview button** (below scores):
Opens a modal overlay containing:
- Audio player — user mic and AI TTS mixed on a shared timeline (Web Audio API, browser-side)
- Progress bar with colored flag markers overlaid:
  - Red = Technical Correctness flag
  - Orange = Problem-Solving flag
  - Yellow = Communication flag
  - Blue = Voice flag
- Clicking any flag marker jumps audio to that timestamp
- Interleaved transcript beside the audio player — both sides of the conversation,
  each turn labeled "Interviewer" or "You", scrolls in sync as audio plays


**Per-question breakdown** (one section per question, in order):

For each question:
```
Question N: [Question text]
─────────────────────────────
Correctness: X.X / 10

AI Feedback:
  What went well: [generated text]
  What to improve: [generated text]
  Overall: [1-2 sentence summary]

Flags:
  • [timestamp] Jumped to solution without clarifying scope
  • [timestamp] Filler word cluster (5 in 15 seconds)
  • [timestamp] Great clarifying question

[Retry this question]
```

---

#### Screen: Company Explorer

Accessed from home screen. Company list → company detail.

**Company detail page:**
- Company name
- Interviewer style description (from `interviewer_persona` field)
- Known focus areas (from `known_focus_areas`)
- Round cards — one per round in `company_rounds`:
  - Round name
  - Duration
  - Question range (e.g., "1–2 questions")
  - What it covers (`focus` field)
  - Interview style notes (e.g., "Hints are deducted from scoring" for Google)

No mock interview starts from this screen. It is read-only reference material.

---

### 2.5 Audio Pipeline

The audio pipeline has three sub-systems working in sequence on every user turn.

#### 2.5.1 Audio Capture and Turn Detection

**Feeding schedule: turn-based. Haiku is called only at the end of each complete user statement — never on partial transcripts, never on a continuous timer.**

This mirrors real interviewer behavior: a human interviewer waits for you to finish your thought before responding. Feeding partial transcripts to Haiku mid-sentence would cause interruptions — wrong for an interview simulation.

**Total latency per turn:**
- Deepgram `utterance_end` fires (~1 second of silence after speech): ~instant from backend perspective
- Deepgram final transcript already ready (was streaming in real time): ~0ms additional wait
- Haiku generates response: ~300–500ms
- ElevenLabs first audio chunk: ~300ms
- **~1.5–2 seconds before user hears the AI respond** — acceptable for MVP; see mvp2-pre-launch.md for Silero VAD upgrade path

**Audio capture flow:**
1. Browser captures microphone audio using `MediaRecorder API` (webm-opus) and streams
   raw audio chunks to the backend over WebSocket continuously.
2. Backend forwards the audio stream directly to **Deepgram** (persistent WebSocket connection).
   - Deepgram streams partial transcripts in real time
   - Deepgram fires `utterance_end` event when it detects ~1 second of silence — this is the turn-end signal
3. On `utterance_end`: backend takes the final Deepgram transcript for this turn
4. Backend appends current pseudocode tab content (if coding question) to the transcript
5. Full package sent to Haiku → response generated → sent to ElevenLabs → audio streamed back

> **No separate VAD for MVP.** Deepgram's `utterance_end` handles turn detection. No PCM decode step needed.
>
> **Architecture note — Silero swap-in seam:** Turn detection must be isolated behind a single handler
> function. All downstream logic (transcript retrieval, pseudocode append, Haiku trigger) is called
> from this one function — never inline in the Deepgram event handler. When Silero is added later,
> only the trigger changes. Nothing else in the pipeline needs to know which system fired the signal.
>
> ```python
> # audio/turn_detection.py
> async def on_turn_complete(session_id: str, transcript: str):
>     """Single entry point for turn-end. Called by Deepgram now, Silero later."""
>     # append pseudocode, trigger haiku, etc.
>     ...
>
> # Deepgram handler (MVP):
> if event.type == "utterance_end":
>     transcript = get_final_transcript(event)
>     await on_turn_complete(session_id, transcript)
>
> # Silero handler (future — on_turn_complete is unchanged):
> if silero_detects_speech_end(audio_chunk):
>     transcript = await deepgram_transcribe(buffered_audio)
>     await on_turn_complete(session_id, transcript)
> ```

**Coding inactivity exception — the only proactive Haiku trigger:**

In a real coding interview, the interviewer watches code appear on screen and stays quiet
as long as the candidate is making progress. They only nudge when the candidate has gone
completely still — no talking AND no typing. That is the signal of being stuck.

This is an **inactivity timer**, not a silence timer. The distinction matters:
- Silent but typing → working, do not interrupt
- Silent AND stopped typing → potentially stuck, start the clock
- Silent AND stopped typing for threshold duration → nudge

**How it works:**
- Inactivity timer is active only when `question.category = coding`
- Timer resets on either: a completed speech turn OR a `pseudocode_update` event from the frontend
- Frontend sends `{"type": "pseudocode_update", "content": "..."}` debounced at 1 second —
  fires once per second of continuous typing, not on every keystroke
- If timer reaches threshold with no speech AND no typing: backend proactively triggers Haiku
  with the current pseudocode state
- Haiku responds with a think-aloud nudge: "I can see you're working through something —
  what's your approach so far?"
- Delivered via TTS the same as any other response

**Thresholds (randomized to prevent gaming):**
- Verbal questions — silence timer: randomized, centered around 20–30 seconds
- Coding questions — inactivity timer: randomized, centered around 45–60 seconds
  (a longer threshold because even complete stillness during coding is often just thinking)

**Full feeding schedule:**
```
Normal flow (all question types):
  User speaks
  → Deepgram utterance_end fires (~500ms silence)
  → Final transcript retrieved
  → [If coding question: append current pseudocode tab content]
  → Haiku called with: transcript + pseudocode + context
  → Haiku generates response
  → ElevenLabs TTS → audio streamed to frontend

Coding inactivity exception (coding questions only):
  45–60s inactivity timer fires (no speech AND no typing)
  → Backend reads current pseudocode state
  → Haiku called with: pseudocode + "candidate has been inactive for X seconds"
  → Haiku generates think-aloud nudge
  → ElevenLabs TTS → audio streamed to frontend
```

Haiku is never called on partial transcripts, never on a fixed interval, never mid-sentence.
Every Haiku call is triggered by either a completed speech turn or the coding inactivity timer.

#### 2.5.2 Speech-to-Text (Deepgram)

**Connection:** Backend maintains a persistent Deepgram WebSocket connection for the
duration of the session. Audio chunks from the frontend are forwarded to Deepgram
in real time.

**Configuration:**
```python
deepgram_options = {
    "model": "nova-2",
    "language": "en-US",
    "encoding": "webm-opus",   # Chrome MediaRecorder default — no decode step needed
    "sample_rate": 16000,
    "filler_words": True,      # preserve um, uh, like, you know in transcript
    "smart_format": True,
    "punctuate": True,
    "utterances": True,        # enables utterance_end event — this is our turn-end signal
    "utterance_end_ms": 500,   # fire after 500ms silence — lowest practical value before mid-sentence false positives
    "words": True              # return word-level timestamps (needed for audio flag mapping)
}
```

**Output:** Deepgram returns:
- Full transcript text (with filler words preserved)
- Word-level timestamps (start/end seconds for each word)
- Confidence scores

The transcript and word timestamps are stored per-turn in the session. Word timestamps
are used post-session to map Domain Expert flags to audio positions for the replay timeline.

#### 2.5.3 Text-to-Speech (ElevenLabs)

**When triggered:** After the orchestrator (Claude Haiku) generates a response text.

**Process:**
1. Backend sends response text to ElevenLabs Turbo v2 API (streaming mode, `output_format: "webm_opus"`)
2. ElevenLabs returns audio chunks as they are generated (~300ms to first chunk)
3. Backend streams audio chunks to frontend as binary WebSocket frames
4. Frontend plays chunks progressively using **MediaSource Extensions (MSE)**

**Frontend TTS playback — MSE:**

MSE is purpose-built for streaming media chunk-by-chunk into an HTML5 audio element.
It handles webm-opus natively — the codec header in the first chunk sets up the decoder,
and subsequent chunks append seamlessly. The browser manages all buffering and timing.

```js
// Initialised once when the interview begins
const audio = new Audio()
const mediaSource = new MediaSource()
audio.src = URL.createObjectURL(mediaSource)
let sourceBuffer

mediaSource.addEventListener('sourceopen', () => {
  sourceBuffer = mediaSource.addSourceBuffer('audio/webm; codecs="opus"')
  audio.play()
})

// Called for each binary WebSocket frame during AI turns
function onTTSChunk(arrayBuffer) {
  if (sourceBuffer && !sourceBuffer.updating) {
    sourceBuffer.appendBuffer(arrayBuffer)
  }
  // If sourceBuffer.updating, queue the chunk and append on 'updateend' event
}
```

Backend sends `{"type": "ai_turn_start"}` before the first chunk and `{"type": "ai_turn_end"}`
after the last chunk — frontend uses these to show/hide the mic indicator.

**Watch Interview modal — separate system:**
Audio replay in the Watch Interview modal uses the **Web Audio API** to mix the two stored
files (user mic + AI TTS) on a shared timeline. MSE and Web Audio API are used in different
contexts and never run simultaneously — MSE during the live interview, Web Audio API in the
replay modal only.

**Voice selection — randomized pool:**

ElevenLabs has an "Interviewer" voice category with professional, neutral voices.
The implementation:

1. Curate a pool of 20 voices from ElevenLabs — listen to samples, hand-pick those that
   sound like real professional interviewers (neutral American/British English, clear,
   professional tone). Mix of male and female voices. Each voice gets a paired name.
   Store in a config file.

2. At session start, randomly select one voice from the pool. That voice (and its paired
   name) is used for the entire session — consistent within a session, different between sessions.

3. Randomize the `stability` parameter slightly per session (0.4–0.6 range). Controls
   how emotionally varied the delivery is. Adds natural micro-variation without sounding
   like a different person.

```python
# config/voices.py
INTERVIEWER_VOICE_POOL = [
    {"voice_id": "abc123", "name": "Alex"},
    {"voice_id": "def456", "name": "Sarah"},
    {"voice_id": "ghi789", "name": "Marcus"},
    {"voice_id": "jkl012", "name": "Priya"},
    # ... 20 total, curated from ElevenLabs — hand-picked from samples
]

# At session start:
import random
session_voice = random.choice(INTERVIEWER_VOICE_POOL)
session_voice_id = session_voice["voice_id"]
session_interviewer_name = session_voice["name"]   # injected into orchestrator system prompt
session_stability = random.uniform(0.4, 0.6)
```

Result: 20 distinct interviewer voices, each with a matching name. Consistent within
a session, different between sessions. Large pool minimizes repetition across many sessions.

**Audio recording — two separate files, saved by the backend:**

The backend saves both audio streams simultaneously as they flow through it:

- **User mic** (`audio_path_user`): audio chunks arrive from the frontend → forwarded to Deepgram AND written to `AUDIO_STORAGE_PATH/{session_id}_user.webm` simultaneously. Same chunks, two destinations.
- **AI TTS** (`audio_path_ai`): ElevenLabs chunks arrive at the backend → forwarded to the frontend AND written to `AUDIO_STORAGE_PATH/{session_id}_ai.webm` simultaneously.

Both files are written as the session runs — no post-session processing needed. Mixed only at replay time in the Watch Interview modal (Web Audio API, browser-side).

### 2.6 Question Selection Algorithm

Runs at session start (during waiting room). Backend executes:

**Step 1 — Determine question pool size:**
Look up `company_rounds.question_count_range` for the selected company + round (e.g., `[1, 2]`).
Pre-select `max(question_count_range)` questions — the maximum possible. The actual number
delivered depends on time: guaranteed to reach `min(question_count_range)`, opportunistically
reaching the max if the candidate moves quickly. Per-question time budget is calculated from
`min(question_count_range)` to guarantee the minimum is always reached.

**Step 2 — Category filter:**
- If `company_rounds.is_technical_only = true`: filter question pool to
  `category IN ('technical', 'coding', 'system_design')` only.
- Otherwise: use `company_rounds.category_weights` as sampling probabilities.
- For MVP, all rounds are weighted heavily toward technical. Behavioral weight is ≤0.05
  across all companies.

**Step 3 — Build pool:**
Query: active questions matching `company_id` + `role_id` (if role is linked to questions)
+ category filter.

**Step 4 — Fallback if pool < 2 × N:**
If the filtered pool has fewer than 2 × N questions, augment:
1. Pull from `company.similar_companies` (in order, most similar first) with a 0.7×
   quality score multiplier applied to fallback questions.
2. If still insufficient, pull from `role.similar_roles` for the same company.
3. Do not tell the user. The interview should feel native to the selected company.

**Step 5 — Weighted random selection:**
Select N questions without replacement using `quality_score²` as selection weight.
Squaring amplifies the gap — a 0.9 quality question is ~3× more likely than a 0.5
quality question. This ensures high-quality questions dominate while preserving variety
across sessions.

**Step 6 — Order questions:**
Shuffle selected questions in random order for MVP. Question ordering strategy
(difficulty-based, category-based, adaptive) is a post-MVP improvement.

**Step 7 — Generate briefings:**
Fire N parallel Claude Sonnet calls via `asyncio.gather()` — one call per selected question.
Each call receives one question and returns one briefing JSON. All briefings stored in
`session.question_briefings`. Total latency ≈ one Sonnet call regardless of question count.
These are the only pre-session Sonnet calls.

**Briefing format per question:**
```json
{
  "question_id": "...",
  "question": "Design a URL shortening service like bit.ly",
  "category": "system_design",
  "triggers_coding_tab": false,
  "ideal_answer_summary": "Cover: hashing strategy, database schema, read-heavy caching layer (Redis), CDN for global redirect speed. Key insight: reads vastly outnumber writes.",
  "key_concepts": ["consistent hashing", "base62 encoding", "CDN", "read/write ratio"],
  "common_wrong_paths": [
    {
      "path": "Focuses on shortening algorithm without addressing scale",
      "signal": "Talks only about hashing with no mention of read volume",
      "response": "How many redirects per day do you think this service handles?"
    },
    {
      "path": "Skips caching entirely",
      "signal": "Describes hitting the database on every redirect",
      "response": "What happens to your database at 10 billion requests per day?"
    }
  ],
  "good_signals": [
    "Asks about expected scale before designing",
    "Separates read path from write path early"
  ],
  "hint_if_stuck": "Ask: What's the ratio of people creating short links vs. clicking them?"
}
```

### 2.7 Orchestrator (Claude Haiku)

The orchestrator runs the live interview. It is the only model called in real time.
It must respond in under 500ms to maintain conversational feel.

#### 2.7.1 Context Assembly

The orchestrator's context window is kept minimal at all times to preserve low latency.
Context is assembled from components pulled from the session record.

**What is in context at any moment:**

```
[SYSTEM PROMPT]

You are {interviewer_name}, a {round_name} interviewer at {company}.

{company_profile.interviewer_persona}

INTERVIEW BEHAVIOR RULES:
- Never say an answer is wrong directly. Redirect via test cases, constraint narrowing, or probing questions.
- Hint sequence (in order): introduce a failing test case → narrow a constraint → single-word nudge → direct redirect
- Intervene after 2-3 minutes of unproductive stagnation, or immediately if a major flaw is visible
- Track hints given. Each hint given reduces the candidate's problem-solving score (handled in post-session analysis).
- Move to the next question only after exhausting the hint sequence or when time is nearly up.
- Never confirm an answer is correct mid-interview. Stay neutral.
- Verbal time warning when appropriate: "You have about X minutes left."

COMPANY-SPECIFIC BEHAVIOR:
{company_profile.wrong_answer_response}
Hint frequency: {company_profile.hint_frequency}
Hint style: {company_profile.hint_style}
Modifies problem mid-interview: {company_profile.modifies_problem_mid_interview}

CURRENT SESSION:
Role: {role}
Round: {round_name}

COMPLETED QUESTIONS (summaries only):
Q1: [1-3 sentence compressed summary]
Q2: [1-3 sentence compressed summary]

CURRENT QUESTION:
{question_text}

BRIEFING (do not reveal to candidate):
Ideal answer: {briefing.ideal_answer_summary}
Wrong paths to watch for: {briefing.common_wrong_paths}
Good signals: {briefing.good_signals}
Hint if stuck: {briefing.hint_if_stuck}

[CONVERSATION HISTORY — current question only]
Interviewer: [question asked]
Candidate: [response]
Interviewer: [follow-up]
...
```

**What is never in the context window:**
- Briefings for any question other than the current one
- Full transcripts from completed questions (only compressed summaries)
- Any data not needed for the current turn

#### 2.7.2 Pseudocode Integration

When the current question's `category = coding`, the pseudocode tab content is
appended to each user message before it reaches the orchestrator:

```
[Candidate's spoken turn transcript]

[Current pseudocode — as of this turn]:
"""
{pseudocode_tab_content}
"""
```

The orchestrator reads the pseudocode as part of the message on every turn. It can
reference what's being written, ask about the approach, and intervene on a wrong path
before the candidate wastes time on it — exactly how a real interviewer in CoderPad behaves.

#### 2.7.3 Interview Opening

The opening must complete in under 1 minute. Users know they're talking to an AI —
a long intro is a waste of their time. Get in, establish the human feel, and get to
the first question fast.

**Hardcoded structure (total: under 60 seconds):**

1. Interviewer introduces themselves: "Hi, I'm Alex from Google's engineering team."
2. One — and only one — small talk exchange. ("Ready to get started?" / "How are you doing today?" — single question, single response, move on.)
3. One-sentence interview framing: "I'll ask you a couple of technical questions — feel free to think out loud as you go."
4. First question asked immediately.

**System prompt instruction:**
```
Keep the interview opening under 60 seconds total. One brief small talk exchange only —
do not extend it. Frame the interview in one sentence, then ask the first question.
```

**Hard enforcement — 60-second opening timer:**
Backend starts a 60-second timer when the WebSocket opens. If the first question has not
been asked by the time the timer fires (tracked by `session.current_question_index` still
being 0 with no question turns logged), backend injects:
```
[SYSTEM: Begin the interview now. Ask the first question immediately.]
```
This is a safety net — the system prompt instructions should keep the opening under 60
seconds naturally. The timer prevents a runaway opening in edge cases.

**Time budget formula update:** Opening budget reduced to 1 minute (from 3).
```
working_time = duration_minutes - 1 (opening) - 1 (closing)
per_question_budget = working_time / min(question_count_range)
```

#### 2.7.4 Question Transitions

The orchestrator signals a question transition in its response text using a structured
marker that the backend parses:

```
[QUESTION_COMPLETE]
```

When the backend sees this marker, it does two things **simultaneously** — one blocking, one async in the background. The main pipeline never waits for compression.

**Main pipeline (blocking — runs at full speed):**
1. Strip `[QUESTION_COMPLETE]` from the text before sending to TTS
2. Advance session to the next question index
3. Load next question's briefing from `session.question_briefings`
4. Assemble updated orchestrator context (new briefing in, old briefing out)
5. Orchestrator generates transition ("Great, let's move on...") → TTS → user hears it

Zero added latency between questions from the user's perspective.

**Background compression (non-blocking — fired with `asyncio.create_task()`):**
```python
async def compress_question(session_id, question_id, full_transcript):
    summary = await haiku.complete(
        system="Summarize this interview question exchange in 1-3 sentences. "
               "Include: what the question was, whether the candidate got it, "
               "how many hints were needed, and any notable strengths or weaknesses.",
        user=full_transcript
    )
    await db.update_session_summary(session_id, question_id, summary)

# In the transition handler — fires and returns immediately:
asyncio.create_task(compress_question(session_id, question_id, transcript))
# Main pipeline continues without waiting
```

The summary is written to `session.question_summaries[question_id]` when ready
(~1-2 seconds later). It appears in the orchestrator's context from the next
question onward. If compression hasn't finished before the next question starts
(edge case), that question runs without the summary — it appears one question later.
Acceptable for MVP.

**What compression does to the full transcript:**
The full turn-by-turn transcript for the completed question is stored permanently in
`session.question_transcripts[question_id]` for post-session Domain Expert scoring.
Compression creates a separate short summary for the orchestrator's live context.
These are two different fields serving two different purposes.

#### 2.7.5 Interview Closing

**Trigger:** After the final question's `[QUESTION_COMPLETE]` fires and the backend detects
no more questions in the queue (all `max(question_count_range)` questions exhausted, or
`session_time_remaining < 3 min`), the backend injects into Haiku's context:

```
[SYSTEM: All questions complete. Deliver the interview closing naturally. After the
candidate responds (1-2 exchanges maximum), include [SESSION_COMPLETE] in your final message.]
```

Haiku delivers a natural outro:
> "That's all the questions I have for you today. Thank you for your time — we really
> appreciate you coming in. We'll be in touch soon. Do you have any questions for me?"

The user can respond or say they have no questions. Haiku handles 1-2 exchanges, then
closes naturally and includes `[SESSION_COMPLETE]` in its final message.

**`[SESSION_COMPLETE]` handling:**
- Backend strips the marker before sending to ElevenLabs (never spoken aloud)
- Backend sets `session.status = 'completed'`, `session.ended_at = now()`
- Closes the WebSocket
- Stops recording
- Sends `{"type": "session_end"}` to frontend → frontend transitions to Analysis Loading

#### 2.7.6 Pause and Resume

**Pause:**
1. User clicks Pause button on interview screen
2. Frontend sends `{"type": "pause"}` over WebSocket
3. Backend: stops silence/inactivity timers, saves session state, sets `session.paused_at_question`
   to the current question index, closes WebSocket
4. Recording paused (frontend stops buffering audio)
5. Frontend shows pause overlay

**Resume:**
1. User clicks Resume
2. New WebSocket connection established
3. Backend reconstructs orchestrator context from session record:
   - Loads company profile
   - Loads compressed summaries of completed questions
   - Loads briefing for current question (the one they paused on)
   - Reconstructs conversation history for the current question from stored turns
4. Orchestrator acknowledges the resume: "Welcome back. We were just discussing [current question]. Where did we leave off?"
5. Recording resumes — appends to same audio file

**On resume:** Full current-question conversation history is reconstructed in context.

**Early exit:**
If user clicks "End Interview" (with confirmation dialog), session is marked
`status = 'abandoned'` if no questions were completed, or `status = 'completed'` if
at least one question was completed. Analysis runs on whatever was completed.

### 2.8 Domain Expert (Claude Sonnet) — Pre-Session

See Section 2.6, Step 7 for the briefing generation flow and format.

The Domain Expert is called once pre-session (batch briefings for all N questions)
and once post-session (scoring). It is never called during the live interview.

---

### 2.9 WebSocket Message Protocol

**Resolves Q14 and Q22.**

The WebSocket carries two types of data simultaneously using the browser's native frame types:
- **Binary frames** — raw audio (both directions)
- **Text frames** — JSON control messages (both directions)

The receiver checks the frame type on every message. No encoding overhead on audio.

```js
// Frontend receive handler:
websocket.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    onTTSChunk(event.data)          // binary = AI audio chunk, feed to MSE
  } else {
    handleEvent(JSON.parse(event.data))  // text = control message
  }
}
```

---

**Backend → Frontend messages (JSON text frames):**

```json
{"type": "session_ready"}
```
Fires when briefing generation completes and the randomized waiting room delay expires.
Frontend transitions from Waiting Room to Live Interview screen.

```json
{"type": "question_start", "question_id": "...", "category": "coding", "triggers_coding_tab": true}
```
Fires at the start of each question. Frontend shows or hides the pseudocode tab based on
`triggers_coding_tab`. Resolves Q22 — this is how the frontend knows which questions need the tab.

```json
{"type": "ai_turn_start"}
```
Fires before the first TTS audio chunk for a given AI turn. Frontend hides the mic indicator
(AI is speaking, candidate should listen).

```json
{"type": "ai_turn_end"}
```
Fires after the last TTS audio chunk for a given AI turn. Frontend shows the mic indicator
(candidate's turn to speak).

```json
{"type": "session_end"}
```
Fires when `[SESSION_COMPLETE]` is received from the orchestrator. Frontend transitions to
Analysis Loading screen.

```json
{"type": "error", "message": "Something went wrong. Please try again."}
```
Any unrecoverable backend error during the session.

---

**Frontend → Backend messages (JSON text frames):**

```json
{"type": "pause"}
```
User clicked Pause. Backend stops silence/inactivity timers, saves session state, closes WebSocket.

```json
{"type": "end_interview"}
```
User confirmed End Interview. Backend closes session, runs analysis on completed questions.

```json
{"type": "pseudocode_update", "content": "function twoSum(nums, target) {\n  ..."}
```
Sent debounced at 1 second when pseudocode tab content changes. Backend resets the coding
inactivity timer and stores latest pseudocode content for the next Haiku call.

---

**Audio frames (binary, both directions):**

```
Frontend → Backend:  raw webm-opus chunks from MediaRecorder (microphone)
Backend → Frontend:  raw webm-opus chunks from ElevenLabs (AI TTS)
```

No JSON envelope. Raw binary. Receiver detects by frame type (`instanceof ArrayBuffer` on
frontend, `bytes` type in FastAPI WebSocket handler on backend).

---

## Part 3: Post-Interview Analysis

### 3.1 Analysis Pipeline

Triggered when the session ends (normally or via early exit with completed questions).

**Input to Domain Expert:**
- `session.question_summaries` — compressed 1-3 sentence summaries per question
- `session.pseudocode` — pseudocode submitted per coding question
- `session.hints_given` — hint count per question
- Full transcript per question (the actual turn-by-turn text, not just the summary —
  the summary was for the orchestrator's context, but the Domain Expert gets the real thing
  for accurate scoring)


**Filler word data:**
Deepgram returns word-level data including filler words (with `filler_words=true`).
This is stored per-turn during the session. For Voice scoring, the Domain Expert
receives a filler word count and rate per question (words per minute, filler words per minute).

**WPM calculation:**
From Deepgram word-level timestamps:
```
wpm = (word_count / (last_word_end_timestamp - first_word_start_timestamp)) * 60
```
Calculated per question and per answer, stored in session, passed to Domain Expert.

### 3.2 Domain Expert Scoring Prompt

The Domain Expert receives the full session data and scores 4 categories:

**System prompt:**
```
You are an expert technical interview evaluator. You will be given a transcript of a
technical mock interview and must score the candidate across 4 categories.

Score each category on a scale of 0.0 to 10.0 with one decimal place.
A score of 7.0 is a solid, hireable performance. 9.0+ is exceptional.

Also generate per-question feedback and flag specific moments in the transcript.

IMPORTANT — flag transcript segments must be verbatim:
When referencing a transcript segment in a flag, copy the EXACT characters from the
transcript. Do not paraphrase, summarize, remove filler words, or alter punctuation in
any way. If the relevant passage is long, shorten it by taking a smaller exact substring —
never by rewriting it. Also include the turn_index (0-based turn number in the transcript)
where the flag occurs.
```

**Input structure per question:**
```
QUESTION {n}: {question_text}
CATEGORY: {category}
HINTS GIVEN: {hint_count}
FILLER WORDS: {filler_count} ({filler_rate}/min)
WPM: {words_per_minute}
PSEUDOCODE (if coding question):
"""
{pseudocode}
"""
TRANSCRIPT:
{full question transcript}
IDEAL ANSWER (for evaluation only — do not reference directly in feedback):
{briefing.ideal_answer_summary}
KEY CONCEPTS EXPECTED: {briefing.key_concepts}
```

**Required output (JSON):**
```json
{
  "scores": {
    "technical_correctness": 7.4,
    "problem_solving": 6.8,
    "communication": 8.1,
    "voice": 7.0
  },
  "per_question": [
    {
      "question_id": "...",
      "correctness_score": 7.4,
      "feedback": {
        "what_went_well": "...",
        "what_to_improve": "...",
        "overall": "..."
      },
      "flags": [
        {
          "transcript_segment": "um so I would probably just use a hash map here",
          "turn_index": 7,
          "category": "problem_solving",
          "flag_text": "Jumped to solution without asking clarifying questions",
          "flag_type": "negative"
        },
        {
          "transcript_segment": "um like yeah um I think um the complexity",
          "turn_index": 12,
          "category": "voice",
          "flag_text": "Filler word cluster (5 in 15 seconds)",
          "flag_type": "negative"
        },
        {
          "transcript_segment": "...",
          "turn_index": 3,
          "category": "problem_solving",
          "flag_text": "Great clarifying question about input constraints",
          "flag_type": "positive"
        }
      ]
    }
  ]
}
```

**Scoring categories:**

1. **Technical Correctness** — Did the candidate get the right answer? Is the pseudocode
   logically correct? Scored per question then averaged. For pseudocode: logical correctness,
   not syntax. For verbal: accuracy against ideal answer summary.

2. **Problem-Solving Approach** — Did they think through the problem before jumping to an answer?
   - Did they ask clarifying questions?
   - Did they break the problem into manageable pieces?
   - Did they think out loud?
   - Hint count is a direct input — more hints = lower score.

3. **Communication** — How clearly did they explain their thinking?
   - Structure and clarity of answers
   - Did they get to the point or ramble?
   - Evaluated from transcript

4. **Voice** — Verbal delivery.
   - Filler word rate (from Deepgram data)
   - WPM (from Deepgram timestamps — flag if significantly too fast or too slow)
   - Flag clusters of filler words

### 3.3 Flag-to-Audio Timestamp Mapping

Flags reference a `transcript_segment` (verbatim text) and `turn_index` (which turn it's from).
To display flags on the audio progress bar, these are mapped to audio timestamps.

**Process:**
1. During the session, Deepgram word-level timestamps are stored per-turn:
   `{turn_index: [{word: string, start: float, end: float}, ...]}`
2. Post-session, for each flag:
   a. Look up the word timestamp array for `flag.turn_index`
   b. Exact substring match `flag.transcript_segment` against the reconstructed turn text
   c. If exact match found: use `start` of the first matching word as the audio position
   d. If not found: fuzzy match (`difflib.SequenceMatcher`) within that turn only
   e. If still not found: fall back to the `start` timestamp of the first word in the turn
3. Store resolved audio positions in `session.analysis` alongside the Domain Expert output

### 3.4 Per-Question Retry

From the Post-Interview Analysis screen, each question has a "Retry this question" button.

**Flow:**
1. User clicks "Retry this question" on question N
2. Backend creates a retry record linked to the original session + question
3. Domain Expert generates a fresh briefing for this question (re-query, not reuse)
4. WebSocket connection opens immediately — no waiting room, no intro small talk
5. Orchestrator receives: company profile + single question briefing + no prior context
6. ~2 second natural delay from setup time before audio begins
7. Orchestrator asks the question directly
8. Mini-session runs exactly like a normal interview question
9. Domain Expert scores the retry attempt
10. Retry analysis is stored permanently, linked to the original question in the session

**How retries appear in the analysis screen:**

Each question section in the analysis has a collapsible sub-tab area below the main
feedback showing all retries for that question:

```
Question 2: Design a URL shortener
─────────────────────────────────────
Correctness: 5.4 / 10

AI Feedback: [original feedback]
Flags: [original flags]

[Retry this question]

▼ Retries (1)
  ┌─ Retry 1 ──────────────────────────
  │ Correctness: 7.1 / 10  (+1.7)
  │ AI Feedback: [retry feedback]
  │ Flags: [retry flags]
  └────────────────────────────────────
```

- Score delta shown vs. original attempt (+1.7, -0.3, etc.)
- Each retry has its own full feedback and flags
- Retries tab is hidden if no retries exist for that question
- No limit on number of retries — all stored permanently
- User can retry again from within the retry view

### 3.5 Scoring Display

All scores displayed as `X.X / 10` (one decimal place). Examples: 7.4, 8.1, 5.6.
Decimal scoring feels more precise and earned than whole numbers. A 7.4 feels
meaningfully different from a 7.0 in a way that motivates improvement.

**Partial session scoring (early exit with fewer than max questions completed):**
The Domain Expert scores whatever questions were completed. All 4 category scores are
still calculated and displayed — do not hide or skip them. A caveat label appears
beneath the score cards:

```
Based on 1 of 3 questions — scores are less reliable than a full session.
```

The number shown is `completed_questions / max(question_count_range)`. The per-question
breakdown only shows the questions that were actually completed. No empty placeholders
for skipped questions.

---

## Open Questions

All decisions resolved. Full resolution log below.

1. ~~Backend language~~ — Python + FastAPI.
2. ~~Turn detection~~ — Deepgram `utterance_end` (500ms threshold). No separate VAD for MVP. Silero VAD is a high-priority post-MVP latency upgrade — see mvp2-pre-launch.md.
3. ~~Waiting room states~~ — Two states: "Preparing your interview..." during briefing generation, then "Your interviewer will join shortly..." for the intentional delay.
4. ~~Watch Interview label~~ — Keep as "Watch Interview" for MVP.
5. ~~Flag-to-audio mapping~~ — Deepgram word-level timestamps + `turn_index` field on flags. Exact substring match first, fuzzy fallback within the same turn.
6. ~~Timers~~ — Verbal questions: silence timer, randomized 20–30s. Coding questions: inactivity timer (no speech AND no typing), randomized 45–60s. Pseudocode updates debounced at 1s reset the coding inactivity timer.
7. ~~ElevenLabs voice~~ — Pool of 20 curated voices, each with a paired name. One selected randomly per session. `stability` randomized 0.4–0.6.
8. ~~Audio storage~~ — Two separate files (user mic + AI TTS), saved by backend simultaneously as streams pass through. Mixed only at replay time in Watch Interview modal (Web Audio API).
9. ~~Question ordering~~ — Random for MVP.
10. ~~Question compression~~ — Async Haiku call fired immediately on `[QUESTION_COMPLETE]`. Main pipeline never waits.
11. ~~Resume history~~ — Full current-question conversation history reconstructed on resume.
12. ~~Full transcripts~~ — `question_transcripts` stores full turn-by-turn transcript per question, separate from `question_summaries`.
13. ~~Retry analysis~~ — Full new analysis generated per retry. Stored in `sessions.retries` JSON field. Shown as collapsible sub-tabs with score delta.
14. ~~WebSocket protocol~~ — Mixed-mode: binary frames for audio, JSON text for control. Full spec in Section 2.9.
15. ~~Audio encoding~~ — webm-opus end-to-end. No decode step needed.
16. ~~Deepgram utterance_end config~~ — `utterance_end_ms: 500`.
17. ~~Filler word storage~~ — `question_voice_stats` field: `{filler_count, filler_rate_per_min, wpm}` per question.
18. ~~Question time budget~~ — `(duration - 2min) / min(question_count_range)`. Hard backstop with soft warning at 80%, wrap-up nudge at 100%. 3-minute session-end threshold prevents new questions starting too late.
19. ~~Hint tracking~~ — `[HINT]` marker in orchestrator responses, stripped before TTS.
20. ~~Interviewer name~~ — Paired to voice. 20 voice+name pairs in pool.
21. ~~Domain Expert briefings~~ — N parallel async Sonnet calls via `asyncio.gather()`.
22. ~~Pseudocode tab notification~~ — `{"type": "question_start", "triggers_coding_tab": true}` WebSocket message.
23. ~~Flag matching~~ — Verbatim transcript segments + `turn_index`. Exact match first, fuzzy within same turn as fallback.
24. ~~Watch Interview audio~~ — Interleaved view, both tracks on shared timeline, Web Audio API mixing.
25. ~~Early exit (zero questions)~~ — "Interview Ended" screen, one button back to home.
26. ~~Retry context~~ — Orchestrator knows it's a retry, skips small talk, no memory of previous attempt.

---

## All Implementation Questions — Resolved

### Audio Pipeline

**~~14. WebSocket message protocol — not specified.~~** — resolved: mixed-mode WebSocket. Binary frames for audio (both directions), JSON text frames for all control messages. Full message spec in Section 2.9.

**~~15. Audio encoding and the Silero VAD decode step.~~** — resolved: No decode step needed. Browser sends webm-opus via MediaRecorder (Chrome default). Backend forwards directly to Deepgram — no separate VAD, no PCM conversion. Silero VAD is deferred to post-MVP (see mvp2-pre-launch.md).

**~~16. Silero VAD vs. Deepgram utterances — which triggers the Haiku call?~~** — resolved: Deepgram's `utterance_end` event is the sole turn-end signal for MVP. Silero VAD is not used. `utterance_end_ms: 1000` fires after 1 second of silence. Haiku is triggered on `utterance_end`. Silero is a high-priority MVP2 upgrade — reduces response latency by ~0.5–1s. See mvp2-pre-launch.md.

**~~17. Filler word storage — not in sessions table schema.~~** — resolved: separate `question_voice_stats` field in the sessions table. Stores `{filler_count, filler_rate_per_min, wpm}` per question, pre-aggregated from Deepgram word-level data as each question completes. Domain Expert receives clean numbers directly — no parsing of raw Deepgram objects at scoring time.

---

### Orchestrator

**~~18. `[QUESTION_COMPLETE]` reliability and time-based fallback.~~** — resolved:

**Time budget model:**
- `[QUESTION_COMPLETE]` is still the primary transition signal — Haiku fires it when hints are exhausted or the candidate has clearly finished.
- Backend enforces a per-question time budget as a hard backstop. Budget formula:
  ```
  working_time = duration_minutes - opening_budget (1 min) - closing_budget (1 min)
  per_question_budget = working_time / min(question_count_range)
  ```
  Dividing by the *minimum* question count gives the largest possible per-question budget.
  Questions beyond the minimum are opportunistic — they happen if time remains after the
  minimum questions complete. This guarantees the minimum is always reached while
  allowing the maximum when the candidate moves quickly.

**Effective budget — per-question budget is always capped by remaining session time:**
```
per_question_budget = working_time / min(question_count_range)
effective_budget = min(per_question_budget, session_time_remaining)
```
This is calculated fresh at the start of each question. If the session is running long,
the current question automatically inherits whatever time is left rather than running
over the session end.

**Two-stage time enforcement per question (based on effective_budget):**
1. **Soft warning at 80% of effective_budget** — backend injects into Haiku's context:
   `[SYSTEM: ~N minutes remaining for this question. Begin wrapping up.]`
   Haiku delivers verbally: "You have about N minutes left on this one."
2. **Hard limit at 100% of effective_budget** — backend injects:
   `[SYSTEM: Time limit reached. Wrap up this question naturally and transition. Do not cut off abruptly.]`
   Haiku closes naturally ("Good — let's move on...") and includes `[QUESTION_COMPLETE]`.

**Collision rule — do not start a new question near session end:**
After every `[QUESTION_COMPLETE]`, before starting the next question, the backend checks:
```
if session_time_remaining < 3 minutes:
    → skip next question entirely
    → inject: [SYSTEM: Session is nearly over. Deliver the interview closing.]
    → Haiku delivers outro, session ends
```
3 minutes is the threshold. A new question never starts if it can't get meaningful time.
If remaining time is between 3–5 minutes, a new question starts but its effective_budget
is capped at whatever remains — the soft warning fires immediately or soon after.

**`[QUESTION_COMPLETE]` stripping:** Always stripped before ElevenLabs. Never spoken aloud.

**Summary — backend time logic at every question transition:**
```
on [QUESTION_COMPLETE] received:
  remaining = session_end_time - now
  if remaining < 3 min:
      fire interview close
  else:
      effective_budget = min(per_question_budget, remaining)
      start next question with effective_budget
      schedule soft_warning at 0.8 * effective_budget
      schedule hard_limit at effective_budget
```

**~~19. Hint tracking — how does the backend detect when Haiku gave a hint?~~** — resolved: Orchestrator tags its own hints with a `[HINT]` marker in the response text, same pattern as `[QUESTION_COMPLETE]`. Backend strips `[HINT]` before passing to ElevenLabs (never spoken aloud) and increments `session.hints_given[question_id]`. This is reliable, requires no heuristics, and gives the Domain Expert accurate hint counts for scoring.

**~~20. Interviewer name — source not specified.~~** — resolved: Name is paired with voice. Each of the 20 voices in the pool has a fixed name. Whichever voice is randomly selected at session start determines the interviewer's name for that session. Consistent within a session, varies between sessions. See voice pool config in Section 2.5.3.

---

### Domain Expert

**~~21. Domain Expert batch call — one API call or N parallel calls?~~** — resolved: N parallel async calls via `asyncio.gather()`, one Sonnet call per question. Each question gets full model attention in a clean focused prompt. Total waiting room time is roughly equal to one call (parallel not sequential).
```python
briefings = await asyncio.gather(*[
    generate_briefing(question) for question in selected_questions
])
```
Also update Section 2.6 Step 7 to reflect this.

**~~22. `triggers_coding_tab` and frontend notification timing.~~** — resolved: backend sends `{"type": "question_start", "question_id": "...", "category": "coding", "triggers_coding_tab": true}` at the start of each question, before any audio. Frontend shows or hides the pseudocode tab based on `triggers_coding_tab`. See Section 2.9.

---

### Post-Session Analysis

**~~23. Flag-to-transcript matching — exact substring or fuzzy?~~** — resolved: prevent paraphrasing at the source + `turn_index` field as backup. Domain Expert prompt explicitly instructs verbatim quoting. Flag output includes both `transcript_segment` (exact verbatim text) and `turn_index` (which turn the flag is from). Matching strategy: exact substring within that turn first → fuzzy match within that turn if exact fails → fall back to start of turn. Fuzzy match is a rare safety net, not the primary path. See updated flag schema in Section 3.2.

**~~24. Watch Interview modal — which audio track does the transcript sync to?~~** — resolved: interleaved combined view. Both tracks play on a shared timeline. Each turn is labeled "Interviewer" or "You" with the transcript scrolling alongside. User mic and AI TTS audio are mixed in the browser at replay time (Web Audio API) — two `AudioBufferSourceNode`s on the same timeline. Flags are pinned to the shared timeline using the audio positions from Section 3.3.

**~~25. Early exit with zero completed questions — UI not specced.~~** — resolved: simple "Interview Ended" screen. One message ("Your interview has ended."), one button ("Start New Interview") that returns to home. No analysis screen, no partial state. Session is stored as `status = 'abandoned'` in the DB but nothing is shown to the user beyond this screen.

---

### Retry

**~~26. Retry — does the orchestrator know it's a retry attempt?~~** — resolved: orchestrator knows it's a retry but receives no memory of the previous attempt. System prompt includes: `"This is a retry session. Go directly to the question — no small talk or introduction."` The previous attempt's transcript, hints, and conversation are not passed in. The interviewer treats the question as completely fresh — no adjusted behavior based on prior performance, no reference to what happened before. Clean slate on the problem, just without the opening ritual.

---

## Environment Setup (Local)

```bash
# Clone repo
git clone https://github.com/[username]/AI-Project
cd AI-Project

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, OPENAI_API_KEY
# AUDIO_STORAGE_PATH=./audio_sessions
# DATABASE_PATH=./interview.db

# Seed database (company profiles, roles, initial questions)
python scripts/seed_db.py

# Run backend
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Build Order Recommendation

Build in this order — each step is testable before the next:

1. **Database schema + seed script** — create all tables, seed company profiles and rounds,
   verify queries work
2. **Question selection algorithm** — write and test the selection logic against the seeded DB
3. **Domain Expert briefing generation** — test Sonnet producing correct briefing JSON
4. **Backend WebSocket server skeleton** — establish connection, send/receive test messages
5. **Deepgram STT integration** — stream audio from frontend → backend → Deepgram → transcript
6. **ElevenLabs TTS integration** — text → backend → ElevenLabs → audio stream → frontend
7. **Orchestrator integration (Claude Haiku)** — full turn: transcript in → Haiku → response text
8. **Full live interview loop** — wire STT + Orchestrator + TTS end-to-end with one hardcoded question
9. **Question selection + briefing injection** — replace hardcoded question with real selection
10. **Context management** — implement question-by-question briefing swap and transcript compression
11. **Pseudocode tab** — add coding tab to frontend, wire content into orchestrator messages
12. **Pause/resume** — implement session state preservation and reconstruction
13. **Post-session analysis** — Domain Expert scoring, flag generation, analysis screen
14. **Audio replay + flag timeline** — implement the Watch Interview modal
15. **Company Explorer** — read-only company profile display
16. **Per-question retry** — mini-session flow
17. **Pre-interview brief + waiting room** — polish the pre-interview flow
18. **End-to-end test** — full session from home screen to analysis

---

## Notes on MVP Constraints

- Everything runs locally. No cloud infrastructure.
- SQLite for database. No migrations framework required for MVP — just run `seed_db.py`.
- Audio stored to local filesystem. Path configurable via env var.
- No authentication. No user accounts. Sessions are anonymous.
- The "demo" framing means reliability on a single machine under controlled conditions
  is the bar — not production-grade reliability.
- Fine-tuning: none in MVP. All model behavior driven by prompt engineering.
- Voice scoring: transcript-based only (Deepgram filler words + WPM). No raw audio analysis.
- Behavioral questions: in the DB but heavily de-weighted. MVP focuses on technical interviews.
