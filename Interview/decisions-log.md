# Interview App — Decisions Log

Every decision made, and why. Reference this when something in the PRD or codebase
seems arbitrary — it isn't.

---

## Speech-to-Text: Deepgram Nova-2

**Decision:** Use Deepgram Nova-2 for MVP. Migrate to self-hosted Whisper later if cost becomes an issue at scale.

**Why Deepgram:**
- Only viable option for real-time streaming transcription. Whisper (both API and self-hosted) is batch-based — it waits until the user finishes speaking, then transcribes. That adds 1-3 seconds of silence after every answer, which kills the conversational feel.
- ~300ms latency vs. 1-3 seconds for Whisper — significant in a live interview simulation.
- Best accuracy on technical vocabulary (algorithm names, CS terms) of all options evaluated.
- 1-day implementation vs. 3-5 days for self-hosted Whisper.
- Cost is negligible at MVP scale (~$0.005/session).

**Why not Whisper (self-hosted):** Batch-based, requires GPU we don't have, fights the tool to make it real-time.
**Why not Whisper (API):** Same batch latency problem, similar cost to Deepgram, worse fit.
**Why not AssemblyAI:** Real-time capable but ~2x the cost and lower accuracy on technical content.

**Revisit when:** GPU infrastructure is in place for the fine-tuned model — at that point self-hosted Whisper becomes viable and eliminates the per-session cost.

---

## Text-to-Speech: ElevenLabs Turbo v2

**Decision:** ElevenLabs for MVP. Migrate to Orpheus (self-hosted) when GPU infrastructure is in place.

**Why ElevenLabs:** After listening to samples of all three options, ElevenLabs is shockingly better than Cartesia and Orpheus. For a product where the AI needs to sound like a real human interviewer, voice quality is part of the core experience. Cartesia and Orpheus are noticeably AI-sounding by comparison.

**Latency fallback:** If ElevenLabs latency becomes a problem, switch to Cartesia first — ~150ms vs ~300ms first audio chunk, still professional-sounding. See interview/knowledge-base/tts-tradeoffs.md.

**Cost:** ~$0.20-0.30/session — negligible at MVP scale.

**Why not Cartesia:** Quality gap was too large after listening to real samples.
**Why not Orpheus:** Open source quality gap even larger. Requires GPU. Post-MVP.

**Revisit when:** GPU infrastructure is live for the fine-tuned model — at that point Orpheus becomes viable and eliminates per-session TTS cost.

---

## Primary LLM Provider: Claude (Anthropic) Only

**Decision:** Claude-only across all LLM calls. No multi-provider abstraction for MVP.

**Why:** Simplest implementation, one API key, one SDK. Multi-provider (pi-ai) adds flexibility but zero benefit at MVP scale with zero users. Can migrate to multi-provider later if Anthropic has reliability or pricing issues.

**Why not multi-provider:** Added setup complexity with no current payoff. Not worth the half-day of extra work at this stage.

**Revisit when:** Anthropic pricing becomes painful or reliability becomes an issue at scale.

---

## Scoring Scale: 10.0 with Decimals

**Decision:** All categories scored out of 10.0 with one decimal place (e.g., 7.4, 8.1).

**Why:** Decimal scoring feels more precise and earned. A 7.4 feels meaningfully
different from a 7.0 in a way that motivates improvement. Whole numbers feel
too coarse for something as nuanced as interview performance.

---

## Think-Aloud Silence Threshold: Randomized (~20-30 seconds)

**Decision:** Silence prompt fires at a randomized interval centered around 20-30
seconds — not a fixed timer.

**Why:** A fixed threshold trains users to game it ("I have exactly 25 seconds").
Randomization mirrors real human interviewers who have different natural tolerance
for silence. Makes the experience feel human rather than mechanical.

---

## Open Source: No

**Decision:** Fully commercial product. No open source components of the product itself.

**Why:** Commercial startup. Code is a competitive advantage.

---

## Behavioral Questions — Stored but Weighted Low in MVP

**Decision:** Behavioral questions are stored in the question bank normally and not filtered at ingestion. They are de-weighted at question selection time in MVP sessions.

**Why:** The MVP targets technical interviews. Not because behavioral questions are wrong to ask, but because the product's focus is technical interview prep and the infrastructure (question bank, scoring) is built for that first. Behavioral questions exist in the data — they just rarely appear in MVP sessions.

**How it works in question selection:**
- Technical rounds (`is_technical_only = true`): behavioral questions are excluded entirely from the pool.
- Mixed rounds: `category_weights` in the round schema controls the probability distribution. MVP default weights heavily toward technical/coding/system_design. Behavioral weight is low (e.g., 0.05) but not zero.
- Post-MVP: behavioral weight can be increased per company as behavioral infrastructure matures (STAR format evaluation, Leadership Principles scoring, etc.).

**Fine-tuning:**
Fine-tuning the conversational model is post-MVP. For MVP, all orchestrator behavior is driven by prompt engineering — company profiles, system prompts, and Domain Expert briefings. Fine-tuning happens when prompt engineering hits a ceiling. It can be done with synthetic examples written by Matthew (not requiring real user session data) — qualitative vision codified into 100-500 (situation → ideal response) pairs.

---

## Interview Types: Technical only (V1)

**Decision:** V1 covers technical interviews only — phone screen style with pseudocode tab for coding questions. Behavioral interviews added later.

**Why:** Technical interview infrastructure (question bank, evaluation logic, scoring) is harder to build and more valuable to prove first. Behavioral is simpler and can be layered on once the technical pipeline works.

---

## Avatar: Audio-only (V1)

**Decision:** No avatar for MVP. Audio only — mimics a phone screen. Questions displayed on screen as text alongside audio.

**Why:** Video avatar latency (~1-4 seconds added) and compute cost ($0.50-2.00/session) make it impractical for MVP. The product can be validated without it. Phone screen simulations are a legitimate and common interview format.

**Revisit when:** Core product is validated with real users and session volume justifies the cost.

---

## Coding Questions: Pseudocode tab (V1)

**Decision:** When a coding question is asked, a pseudocode text area appears alongside the interview. No compiler or code runner for V1. AI evaluates the pseudocode for correctness.

**Why:** Implementing a real compiler (sandboxed code execution, multiple language support) is significant infrastructure. Pseudocode evaluation by the AI is sufficient to test problem-solving ability and is much faster to build. Compiler can be added later.

---

## Business Model: Freemium

**Decision:** Free tier with 3 interviews. Paid subscription for full access.

**Free tier includes:**
- 3 mock interviews
- Live feedback during interview (AI behaves like real interviewer)
- Correctness analysis on answers
- Role selection

**Free tier excludes:**
- Full post-interview analysis dashboard
- Body language scoring
- Voice analysis (filler words, pacing)
- Video replay with footnotes
- Chatbot advisor
- Interview history / progress tracking

**Why freemium:** Lets users experience the core product before paying. 3 sessions is enough to demonstrate value without giving away unlimited use. Locking the analysis dashboard (the most differentiated feature) behind paywall incentivizes upgrade.

---

## Target User: Technical candidates (V1)

**Decision:** MVP targets people preparing for technical interviews at software companies.

**Why:** Technical interviews have the richest publicly available question bank (LeetCode, Glassdoor, Reddit). The infrastructure to evaluate technical answers is more complex and valuable to prove first. Non-technical interviews are easier to add later.

---

## Role Selection — General, Not Company-Specific

**Decision:** Role options are general job roles (Software Engineer, HR Specialist, Electrical Engineer, etc.) — not positions specific to a company. The list shown for a given company is whatever roles we have question data for at that company.

**Why:** Makes the question bank usable across companies. A "Software Engineer" question from Google is useful context for a "Software Engineer" interview at Amazon. General roles also let us grow the bank more naturally — we're not creating company-specific silos.

**Implication:** Question banks per company-role combination will be relatively small early on. The similar company/similar role fallback in question selection handles this — it pulls from analogous company-role pairs when the pool is thin.

**What this looks like in the UI:** User selects Amazon → sees available roles (Software Engineer, Data Scientist, etc. — whatever we have). Roles with no question data for that company don't appear.

---

## Starting Companies: Google, Amazon, Jane Street

**Decision:** Scrape and build question banks for Google, Amazon, and Jane Street first.

**Why Google and Amazon:** Largest publicly available question banks, well-documented interview processes, extremely common target companies for the user base.

**Why Jane Street:** Differentiated — their interviews (OCaml, functional programming, probability, quant) are very different from standard SWE interviews. Adds signal that the platform isn't just LeetCode prep.

**Note:** Jane Street questions will be harder to source — requires more creative scraping (Reddit, blogs, GitHub prep repos). Start with Google or Amazon for the first pipeline proof.

---

## Storage: SQLite (V1)

**Decision:** SQLite for MVP. Migrate to Postgres when scale requires it.

**Why:** Everything runs locally for now — no cloud hosting or database infrastructure. SQLite requires zero setup, works on Mac and Windows (Finn's machine), and is sufficient for a local MVP. Michael's PRD confirms this as the right starting point.

---

## Conversational Orchestrator — Minimal Context Window

**Decision:** Keep the orchestrator's context window as small as possible at all times. More input tokens = more latency (attention is O(n²) with sequence length). Every token in context costs time on every turn.

**What this means in practice:**

**Briefings are loaded question-by-question, not all at once.**
At session start, the Domain Expert generates briefings for all N questions and stores them to the session record in the database. During the interview, only the *current question's* briefing is loaded into the orchestrator's context. When the question is done and the next one begins, the previous briefing is swapped out and the new one is loaded. The orchestrator never holds all briefings simultaneously.

**Completed question transcripts are compressed immediately.**
When a question closes, the full turn-by-turn exchange is compressed into 1-3 sentences ("Q2: LRU Cache — correct approach, missed O(1) requirement, one hint, self-corrected") and stored to the session record. The full exchange is dropped from context. Only the short summary persists.

**What's in the orchestrator's context at any moment:**
```
1. Company profile + interviewer persona         [static, kept minimal]
2. Current question briefing only               [swapped per question]
3. Compressed summaries of completed questions  [short — 1-3 sentences each]
4. Current question's live conversation         [full, this question only]
```

**What is never in context:**
- Briefings for future or past questions
- Full transcripts from completed questions
- Any data that isn't needed for the current turn

**Why:** Haiku latency target is <500ms per turn. A bloated context window at turn 40 of a 50-turn session would meaningfully degrade response time. Keeping context lean makes latency consistent from question 1 to question 5.

**Where briefings live between questions:** Stored in the session record in the database. Retrieved at question transition — not held in memory or context.

---

## Pseudocode Tab — Real-Time Orchestrator Access

**Decision:** The orchestrator receives pseudocode tab content on every turn during a coding question, not just at post-session scoring.

**Why:** Research confirmed real coding interviews are simultaneous voice + coding. The interviewer watches code appear in real time and responds to it mid-solution — "I see you're using a hash map here, what's the space complexity?" The candidate is expected to think aloud while typing. Waiting until the end to evaluate pseudocode does not simulate this.

**Implementation:** When a coding question is active, the current pseudocode tab content is appended to the user's message on each turn before it's sent to the orchestrator. The orchestrator can then reference what's being written, ask about it, or intervene on a wrong approach early.

**Calibration note:** Pause thresholds for silence detection should be higher during coding questions than verbal questions. A 10-second silence during coding is normal thinking; the same silence during a verbal answer signals difficulty.

---

## Voice Scoring — MVP Approach: Transcript-Based

**Decision:** Score the Voice category entirely from transcript text and Deepgram metadata for MVP. No raw audio analysis pipeline.

**Two things to implement from day one:**

1. **Enable `filler_words=true` on Deepgram Nova-2** — Deepgram preserves and flags filler words (um, uh, like, you know) in the transcript when this parameter is set. Standard Whisper strips them. Zero added infrastructure — one config parameter. Filler count and rate feed directly into the Domain Expert's Voice scoring.

2. **WPM from Deepgram word-level timestamps** — Deepgram returns word-level timestamps. Divide word count by duration = speaking rate per answer. Trivial calculation, meaningful signal.

**What this gives us at MVP:** Filler word count/rate, speaking rate (WPM). Good enough for a meaningful Voice score.

**What it misses:** Precise pause detection, pitch/confidence analysis, hesitation patterns. These require raw audio processing — deferred to post-MVP. See `knowledge-base/voice-analysis.md` for the full post-MVP roadmap and tool reference (Silero VAD, CrisperWhisper, librosa).

---

## Scraping Approach: TBD (Finn's decision)

**Options evaluated:** Python + Playwright, Python + BeautifulSoup, pi-mono agentic (TypeScript), Python + LLM extraction.

**Finn's call** — documented in finn-onboarding.md with full tradeoffs.

---

## Model Stack

**Decision:** See ~/Projects/knowledge-base/agents/interview-model-stack.md for full specs.

**Core principle:** High query volume = open source self-hosted. Low volume, quality critical = API.

- Conversational Orchestrator: Haiku API → Qwen2.5-7B self-hosted
- Domain Expert (question gen + scoring): Claude Sonnet API, stays API
- Scraper/Extractor: Phi-3.5-mini self-hosted from day one
- TTS: ElevenLabs → Kokoro/Orpheus
- STT: Deepgram Nova-2
- Embeddings: OpenAI text-embedding-3-small

**Why:** Detailed reasoning in model-stack file. Short version: the conversational orchestrator is called 20-50x per session and must be fast and cheap. The domain expert is called once per session — quality matters more than cost there.

---

## Infrastructure: Local (V1)

**Decision:** Everything runs locally on Matthew and Finn's machines for MVP. No cloud hosting, no managed database.

**Why:** No capital, no infrastructure setup time. Local is sufficient to build and test the product. Cloud migration happens when there are real users.

**Constraint:** Fine-tuning requires 24GB GPU — use RunPod (~$0.50/hr) on-demand when needed. MIT compute cannot be used for commercial projects (confirmed via ORCD policy review).

**Revisit when:** First real users. At that point evaluate Supabase/Neon (managed Postgres) and a simple cloud host (Railway, Render, or Fly.io).
