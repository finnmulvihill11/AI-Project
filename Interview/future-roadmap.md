# Interview App — Future Roadmap

Everything beyond the pre-launch MVP2 requirements. These are features and infrastructure
for after the product is live and validated with real users. Items are grouped by category,
not priority — pull from this based on what users are asking for.

---

## AI Models — Migrate from API to Self-Hosted

| Component | MVP | Future |
|---|---|---|
| Conversational Orchestrator | Claude Haiku API | Qwen2.5-7B self-hosted via vLLM |
| TTS | ElevenLabs API | Orpheus (GPU) or Kokoro (CPU) self-hosted |
| STT | Deepgram API | Self-hosted Whisper (when GPU available) |
| Domain Expert | Claude Sonnet API | Fine-tuned open source model (Llama/Qwen via Unsloth) |
| Scraper/Extractor | Phi-3.5-mini local | Same — already open source from day one |

**Trigger:** GPU infrastructure in place + enough sessions that API cost is painful.

---

## Interview Experience

### Interviewer Difficulty Selector
- **MVP:** One interviewer style (normal — mirrors typical real interviewer behavior)
- **Future:** User selects Easy / Normal / Hard interviewer archetype
  - **Easy:** More hints, more patient, probes more before moving on
  - **Normal:** Mirrors real interviewer behavior
  - **Hard:** Fewer hints, faster pace, less forgiving of silence
- **Why deferred:** Get the normal behavior right first, then parameterize it.

### Dedicated Technical Coding Rounds
- **MVP:** Pseudocode tab only, appears when question category is `coding`
- **Future:** Dedicated technical round type — full coding environment, compiler,
  test cases, multi-language support
- **Why deferred:** Significant infrastructure. MVP proves the interview loop first.

### Video Avatar
- **MVP:** Audio-only, phone screen feel
- **Future:** Tier 2 (2D animated lip sync) → Tier 3 (photorealistic)
- **Why deferred:** Adds $0.50-2.00/session cost and 1-4s latency.

### Behavioral Interviews
- **MVP:** Technical interviews only
- **Future:** STAR format evaluation, Leadership Principles for Amazon, etc.

### System Design Whiteboard
- **MVP:** System design answered verbally
- **Future:** Interactive whiteboard/diagram tool

### Adaptive Difficulty
- **MVP:** Question bank pre-selected at session start
- **Future:** Real-time difficulty adjustment based on session + historical performance

### AI Conversational Reactions
- AI gives natural back-channel signals while user is talking: "uh-huh", "interesting",
  "go on", "can you say more about that?"
- Makes conversation feel less like speaking into a void
- **Why deferred:** Needs careful implementation — wrong timing feels more robotic
  than silence. Validate core interview loop first.

### Timer Toggle
- User can choose before starting: visible countdown timer on screen or no timer
- **Why deferred:** Minor feature, get core experience right first.

### Warm-Up Button
- Quick pre-interview warm-up: user presses a button, one random question pops up
  on screen as text, user can answer it out loud or in their head to get loose
- Not necessarily AI-driven — could just be a random question from the bank
- Separate from selecting a full interview session
- **Why deferred:** Nice-to-have, not core.

### Pressure Simulation
- Should emerge naturally from accurately modeling real interview behavior
- Not a separate mode — more about tuning orchestrator pacing, silence tolerance,
  and follow-up intensity over time
- **Why deferred:** Get normal behavior right first.

---

## Advanced Analysis

### Dual-Model Architecture (Background Analyst)
- **The idea:** Conversational model (Haiku) stays fast and handles real-time dialogue.
  A second model runs in the background with access to the full transcript so far,
  doing deeper analysis — spotting contradictions, tracking what topics the user
  has avoided, noticing patterns — and occasionally feeds a prompt or flag back
  to the conversational model to act on.
- **Why it's interesting:** Separates concerns cleanly. Fast model stays fast.
  Smart analysis happens asynchronously without adding latency to the conversation.
  This is how you implement consistency challenges, topic tracking, and deeper
  behavioral insights without burdening the real-time model.
- **The challenge:** Inter-model communication protocol — how and when does the
  background model feed back to the conversational model? Timing matters a lot.
  A badly timed injection feels jarring.
- **Why deferred:** Core interview loop needs to work first. Meaningful architectural addition.

### Consistency Challenges
- AI circles back mid-session: "Earlier you said X — how does that reconcile
  with what you just said?"
- Trains a skill no existing app addresses
- **Why deferred:** Requires conversational model to hold and reason over earlier context.
  Risk of hallucinated contradictions. Enabled by Dual-Model Architecture above.

### Body Language Analysis
- Camera-based — posture, eye contact, facial expressions
- **Why deferred:** Requires camera access, CV models, tied to avatar milestone.

### Voice Pattern Analysis (Deep)
- **MVP:** Transcript-based. Deepgram `filler_words=true` captures filler words (um/uh/like/you know)
  directly in the transcript. WPM calculated from Deepgram word-level timestamps. Both fed into
  Domain Expert for Voice category scoring.
- **Post-MVP Tier 1 — easy wins (open source, 1-2 days each):**
  - **Silero VAD (precise pauses)** — already runs client-side during the interview. Post-session:
    run it on the recorded audio to extract exact pause lengths and frequency. No new infrastructure.
  - **CrisperWhisper** — open source Whisper variant that transcribes verbatim, capturing every
    filler word explicitly. Replaces standard Whisper if/when STT is self-hosted. Better filler
    detection than Deepgram's API flag.
  - **WPM trend analysis** — speaking rate per question, detect slowdowns under pressure.
- **Post-MVP Tier 2 — medium complexity (librosa, 3-5 days):**
  - Pitch extraction (F0 mean + variance) — narrow pitch range signals nervousness/flat affect
  - Uptalk detection — rising F0 at end of phrases signals uncertainty
  - Hesitation score — combined signal: filler rate + pause frequency + WPM dips + pitch variance
- **Post-MVP Tier 3 — hard (post-launch, requires data):**
  - Vocal fry / creak detection (custom feature engineering)
  - Real-time streaming audio analysis during the interview (not just post-session)
  - Confidence classifier trained on labeled interview data
- Full research and tool reference: `knowledge-base/voice-analysis.md`

### Video Replay with Body Language Footnotes
- **MVP:** Analysis flags overlaid on transcript
- **Future:** Full body language + voice event footnotes synced to video timeline

---

## Product Features

### Video Download / Sharing
- User can download their interview recording
- Or share a replay link with a mentor for feedback
- **Why deferred:** Video storage infrastructure needed first.

### Streak, Habit Tracking, Gamification
- Daily practice streak, XP points, badges
- Motivation mechanics for consistency
- **Why deferred:** Needs user accounts (MVP2) + meaningful session history.

### Email Interview Report
- After the interview, send the full analysis report to the user's email
- So they can reference it later, share with a mentor, or review on mobile
- **Why deferred:** Email infra exists in MVP2 — this is a quick add once that's in place.
  Listed here because it's a nice-to-have, not a launch blocker.

### Percentile Scoring
- "You scored in the top X% of people who practiced this Google SWE phone screen"
- Motivating across the board — even bottom percentile tells you where to improve
- **Options:** Opt-in only, or only shown when above median
- **Why deferred:** Requires meaningful user base to be statistically valid.

### Question Coverage Map
- "You've practiced 0 concurrency questions. Google asks it 40% of the time."
- Requires enough company-specific question data to make the map meaningful
- **Why deferred:** Need better data first, but high value when ready.

### Readiness Score + Calendar Integration
- User enters actual interview date
- App generates calibrated readiness score + personalized study schedule
- "You have 8 days. You're at ~70th percentile. Focus on: system design, concurrency."
- **Why deferred:** Needs user history and enough data to calibrate score.

### Calendar Integration + Post-Interview Survey (HIGH PRIORITY when ready)
This is one of the most valuable future features — it builds the question bank
from real interviews automatically.

**How it works:**
- User enters their actual interview date when setting up prep
- After the interview date passes, app sends automated email or SMS with a survey:
  1. How did your interview go? (1-5 scale + open text)
  2. What rounds did you participate in?
  3. What questions were you asked? (with explicit quality warning)
  4. How do you think you did overall?
  5. What can we improve about our product?

- Submitted questions are reviewed before entering the question bank
- Outcome data (got the job / didn't) powers the readiness score calibration over time

**Why this is so valuable:**
- Real questions from real recent interviews — more current and accurate than scraping
- Round structure data is very hard to get any other way
- Product feedback built into the natural post-interview moment

**Why deferred:** Needs user base, calendar feature, email/SMS infrastructure.

### Per-Question Feedback (HIGH PRIORITY when ready)
After the analysis screen, occasional prompts on individual questions: "Was this a good question? 👍 👎"
- Not shown after every session — surfaced occasionally, or only for questions with low confidence quality scores
- Simple boolean + optional short comment. No friction.
- Thumbs-up/down aggregate back into the question's `quality_score` in the DB
- Session performance aggregates into `difficulty_score` per question
- Questions with many thumbs-down flagged for review (not auto-deleted)

**Why this is valuable:** Human signal on question quality is far more accurate than what the enrichment
model can assign at ingestion. Over time this self-corrects the question bank with almost zero user effort.
**Why deferred:** Needs user accounts and session storage.

### Crowdsourced Question Bank (HIGH PRIORITY when ready)
The post-interview survey is the primary mechanism. Additional crowdsourcing:
- Paid users can submit questions directly from the app at any time
- Clear quality warning on submission
- Questions go through a review queue before entering the bank
- Over time this becomes more valuable than scraped data — fresher, more accurate,
  validated by real candidates

**Why deferred:** Needs user base.

### Intelligent Question Ordering
- **MVP:** Questions presented in random order within a session
- **Future:** Order questions intelligently within a session:
  - Difficulty-based: sort by `difficulty_score` ascending once empirical data exists
  - Category-based: warm up with verbal technical questions before coding/system design
  - Adaptive: real-time reordering based on how the session is going
- **Why deferred:** `difficulty_score` starts null at launch (no real user data yet).
  Random order is fine for MVP and avoids false precision.

### Adaptive Question Targeting
- Question selection weights toward areas the user has historically struggled with
- "You've done poorly on concurrency 3 times — this session will include more of it"
- **Why deferred:** Needs user history.

### Course Integration
- Separate tab: upload syllabus → AI walks through a course
- Connects to interview performance — weak in distributed systems → recommends course
- **Why deferred:** Separate product surface, significant scope.

### B2B Model
- Companies use platform for first-round interviews
- Platform produces rich signal: raw ability, learning speed, commitment, adaptability, communication
- Course integration: gaps identified → targeted courses assigned → candidate reassessed
  ("scored 6.0 raw, brought weak areas to 7.5 after coursework — that learning signal is more
  predictive than a snapshot score")
- ATS integration (Greenhouse, Lever, Workday) required
- **Major legal complexity:** EEOC disparate impact rules, NYC Local Law 144 (bias audits),
  Illinois AI Video Interview Act, EU AI Act (high-risk classification for employment AI)
- Full details: knowledge-base/b2b-model.md
- **Why deferred:** B2C must be validated first. Legal infrastructure for AI-in-hiring is significant
  and separate from B2C legal work..

### Expanded Company Coverage
- **MVP:** Google, Amazon, Jane Street
- **Future:** Each new company is mostly a data problem, not an engineering problem.

---

## Infrastructure

### GPU Infrastructure
- **MVP:** RunPod on-demand for fine-tuning experiments
- **Future:** Dedicated GPU for serving fine-tuned conversational model

### Human-in-the-Loop Data Review
- **MVP:** Pure automation
- **Future:** Human review queue for first N examples per new source

---

## Free Tier Upgrades (if freemium model evolves)
- More than 3 free sessions
- Free access to basic analysis
- Trial of chatbot advisor
