# Interview App — MVP2: Pre-Launch Requirements

These are the things that need to exist before the app can launch to real users.
Not nice-to-haves — blockers. MVP proves the AI interview loop works in isolation.
MVP2 is what turns it into an actual product people can sign up for.

Items are roughly ordered by dependency — user accounts are the prerequisite for most of the rest.

---

## ⚡ Silero VAD — Conversation Latency Upgrade (HIGH PRIORITY)

> **This is the most important technical upgrade between MVP and launch.**
> If the AI response feel is slow during MVP testing, fix this first — before any product feature work.

**The problem:** MVP uses Deepgram's `utterance_end` for turn detection. Deepgram waits ~1 second of silence after you stop talking before firing the signal. That silence gap + Deepgram transcription + Haiku generation + ElevenLabs TTS means the AI responds ~1.5–2 seconds after the user finishes speaking. At 2 seconds this starts to feel like lag, not a conversation.

**The fix — Silero VAD server-side:**
Replace Deepgram `utterance_end` as the turn trigger with Silero VAD running locally on the backend.

```
MVP pipeline:   User stops → Deepgram utterance_end fires (~1s silence) → transcript ready → Haiku
Silero upgrade: User stops → Silero VAD fires (~30–100ms) → send audio to Deepgram → transcript → Haiku
```

**What this requires:**
1. Add `silero-vad` Python package to backend
2. Add a webm-opus → PCM decode step (one function, ~10 lines, using `pydub` or `ffmpeg-python`)
3. Run Silero on incoming audio chunks in 30ms windows
4. On speech-end detection: send buffered audio to Deepgram, trigger Haiku on transcript-ready
5. Disable `utterances: True` in Deepgram config (no longer needed as turn signal)

**Estimated latency improvement:** ~0.5–1 second off every single AI response. Across a 45-minute interview this is the difference between the product feeling like a real conversation and feeling like a voice assistant.

**When to do it:** As soon as MVP testing reveals the response gap is noticeable. Do not block MVP build on this — build it in MVP, test it, and add Silero if the feel is off.

---

## User Accounts and Auth

Everything else in this document depends on this existing first.

- Sign up / log in (email + password minimum; OAuth optional)
- Session tied to user — interviews stored to their account
- Free vs. paid account state tracked per user
- Password reset flow

**Why now:** Cannot gate features, persist history, or bill anyone without accounts.

---

## Legal Agreements and Compliance

Required before any real user can touch the product. Do not launch without these.

> **Note:** This section covers what we know now. Before launching, do deep research
> on every applicable law — BIPA, CCPA, GDPR, state recording consent laws, AI disclosure
> requirements. Laws vary by jurisdiction and this space moves fast. Hire a lawyer or use
> a legal service (Clerky, Stripe Atlas, etc.) to review these before launch.

---

### Terms of Service
- Defines what users can and can't do
- Liability limits / disclaimers (product is for practice — not a guarantee of interview success)
- Acceptable use policy
- What happens when accounts are terminated
- Governing law / dispute resolution (arbitration clause is common for startups)
- **AI Disclosure Requirement:** Several jurisdictions (EU AI Act, some US states) require
  disclosing that the user is interacting with an AI, not a human interviewer. Include
  explicit disclosure in the onboarding flow and in the Terms of Service.
  - Exact language: something like "This interview is conducted by an AI system. You are
    not speaking with a human interviewer."

### Privacy Policy
Required by CCPA (California), GDPR (EU), and increasingly required everywhere.

Must cover:
- What personal data is collected (name, email, voice recordings, interview transcripts,
  scores, usage patterns)
- How it's used (improving the product, AI training — must be explicit if used for training)
- Who it's shared with — list every third-party service:
  - **Deepgram** (STT — receives audio)
  - **ElevenLabs** (TTS — sends text, receives audio)
  - **Anthropic** (LLM — receives transcript text)
  - **Stripe** (payments — receives billing info)
  - **Email provider** (Resend/Postmark/SendGrid — receives email addresses)
  - Any analytics tools
- Data retention policy — how long is data stored, when is it deleted (see below)
- User rights — how to request data deletion, export, or correction (required by CCPA/GDPR)
- Cookie policy (if any tracking cookies used)

### Recording Consent
Audio recording is legally sensitive. This needs to be explicit and unambiguous.

- **One-time consent dialog** before any recording begins — user must actively accept
- Stored to account (MVP2) so returning users don't re-accept every session
- **Two-party consent states:** California, Illinois, Washington, Florida (and others)
  require ALL parties to consent to being recorded. Since the AI isn't a legal party,
  the practical requirement is that the USER consents explicitly to being recorded.
  Use the same consent flow across all states — don't try to geogate.
- Consent language must include: what is being recorded (audio), why (interview simulation,
  potential product improvement), how long it's retained, and how they can request deletion.

### Biometric Data Laws (BIPA and similar)
Voiceprints are biometric data. This is a serious legal exposure area.

**Illinois BIPA (Biometric Information Privacy Act) — highest risk:**
- Applies to any Illinois resident, regardless of where your company is incorporated
- Requires: written policy on retention/destruction, written release signed by subject,
  cannot profit from biometric data without consent
- Private right of action — individuals can sue. Class actions have resulted in
  $650M+ settlements (Facebook, TikTok, others)
- **Action:** BIPA-compliant consent language for all users, not just Illinois residents.
  Easier to comply universally than to geogate.

**Other states to watch:**
- Texas CUBI (Capture or Use of Biometric Identifier) — similar to BIPA, no private right of action
- Washington WBPA — similar, focuses on facial recognition but covers voiceprints
- More states are adding biometric laws regularly — research current state at launch

**Practical approach:**
- Use BIPA-compliant language for all users (strictest standard covers everyone)
- State explicitly: what biometric data is collected, how long it's retained, when it's destroyed
- Do not sell, lease, or profit from biometric data (outside of providing the service itself)
- Destroy data when: user requests deletion, or retention period expires

### Data Retention Policy
Must be defined explicitly and enforced. Decide before launch:

- **Interview recordings (audio):** Retained for X days after session, then automatically deleted
  or retained for account lifetime — choose one. BIPA requires a defined retention/destruction schedule.
- **Transcripts:** Retained until account deletion (probably fine — text, not biometric)
- **Scores and analysis:** Retained until account deletion
- **Account data:** Deleted within 30 days of account deletion request (CCPA/GDPR requirement)
- **Third-party retention:** Deepgram and ElevenLabs have their own data retention policies —
  check their terms, disclose in your Privacy Policy.

### AI Disclosure (Separate from Terms of Service)
Some jurisdictions are moving toward requiring in-context disclosure during AI interactions
(not just buried in ToS). Best practice:
- Show a disclosure banner or screen before the interview starts: "You are about to be
  interviewed by an AI system, not a human."
- Include it in the Pre-Interview Brief screen (already planned in MVP UX).
- EU AI Act (effective 2024-2026 rollout) has explicit transparency requirements for
  AI systems interacting with humans.

---

> **TODO: Deep legal research before launch.**
> This section represents our current understanding. Before the product goes live:
> 1. Audit every state's recording consent and biometric data laws
> 2. Check GDPR applicability if any EU users (likely if the product is public)
> 3. Review EU AI Act obligations (transparency, prohibited practices, high-risk system classification)
> 4. Have a lawyer review the ToS, Privacy Policy, and consent flows — especially the BIPA language
> 5. Confirm what Deepgram, ElevenLabs, and Anthropic's data processing agreements say —
>    GDPR requires Data Processing Agreements (DPAs) with all processors
> 6. Decide whether to restrict access by geography (EU, Illinois) during early launch
>    or comply with all jurisdictions from day one
>
> **Laws to research in depth:** BIPA, CCPA/CPRA, GDPR, EU AI Act, state-level recording
> consent laws, FTC regulations on AI, state-level AI disclosure requirements.

**Why now:** Cannot legally collect voice recordings or personal data without these in place.
Non-compliance with BIPA is the highest-risk exposure — class actions in this space are expensive.

---

## Persistent Session Storage

- Store completed interviews to user account
- Store: questions asked, transcript, scores per category, overall score, session metadata (company, role, round, date)
- Enough to show past interview history — even a basic list is enough for MVP2
- **Not required yet:** Video storage, full replay (those are Future Roadmap)

**Why now:** Users need to see their history to find the product valuable long-term.
Also required for progress tracking and readiness scoring later.

---

## Cloud Hosting

- **MVP:** Local only (Matthew and Finn's machines)
- **MVP2:** Deploy to a real server so users outside the two of you can access it
- Recommended path: Railway, Render, or Fly.io + Neon or Supabase (managed Postgres)
- Domain name + HTTPS (required for any real product)

**Trigger:** First real users. Don't over-engineer — simplest cloud deploy that works.

---

## Postgres Migration

- **MVP:** SQLite
- **MVP2:** Postgres — required for concurrent users on a shared server
- Neon or Supabase both provide managed Postgres with free tiers

**Trigger:** Moving to cloud hosting. SQLite doesn't work for concurrent multi-user access on a server.

---

## Free / Paid Gating

- Enforce the 3-session free tier limit per account
- Payment integration (Stripe) for paid subscription
- Sessions-remaining counter shown to free tier users
- Paywall screen when free sessions are exhausted — converts to paid
- Paid access unlocks: full post-interview analysis dashboard, voice analysis, chatbot advisor (when built)

**Why now:** Cannot monetize without this. Free tier without a hard limit is just a free product.

---

## Dashboard

Minimal dashboard — replaces the current single-screen MVP flow.

**Tabs:**
- **Start Interview** — company + role + round selection, same as MVP
- **Past Interviews** — list of completed sessions with date, company, role, score
- **Account** — subscription status, sessions remaining (free tier), billing link

**Not required yet for MVP2:**
- Full analysis per past session (just show score + metadata in the list)
- Progress tracking graphs
- My Profile (target companies, timeline, self-reported skills)

**Why now:** Users need somewhere to go after their first interview. No dashboard = no retention.

---

## Email Infrastructure

Minimum: transactional email (welcome, password reset, receipt).

**Post-MVP2 but enabled by this:**
- Post-interview analysis emailed to user after session (can implement once email infra exists)
- Post-interview survey for calendar integration users

**Provider:** Resend, Postmark, or SendGrid. One of these needs to be set up before launch.

---

## Candidate Name in Interviews

Once user accounts exist, the candidate's name (from their account profile) is injected
into the orchestrator system prompt at session start:

```
Candidate name: {user.first_name}
```

This allows the interviewer to address the candidate by name naturally during the session
("Great answer, [Name]", "How are you doing today, [Name]?"), which meaningfully improves
the realism of the simulation.

**Not in MVP:** MVP has no accounts, so no name is available. The interviewer never
addresses the candidate by name — just uses "you" naturally.

**When to add:** Immediately after user account infrastructure is live. One-line change
to the orchestrator system prompt assembly.

---

## Resume Upload and Parsing

Tie directly to user account creation — do not build before accounts exist.

**How it works:**
- User uploads their resume during onboarding or from their profile page
- Resume is parsed and key information extracted: skills, experience, past roles, education
- This data is injected into the question selection and orchestrator context so the interview
  can be calibrated to the candidate's actual background
- Example uses: "Candidate has 2 years of Python experience but no distributed systems background —
  weight question selection toward systems fundamentals" or "Candidate lists Redis on resume —
  skip basic caching hints, probe deeper"

**Why this matters:**
A generic interview treats every candidate the same. Resume data lets the system personalize
difficulty, question weighting, and the Domain Expert's scoring context to who the person
actually is. It's a meaningful product upgrade that requires almost no new infrastructure
once accounts and file upload exist.

**Implementation when ready:**
- File upload (PDF, DOCX) stored to user account
- Claude Sonnet parses resume into structured JSON (skills, experience level, companies, roles)
- Structured data stored on user profile
- Injected into Domain Expert briefing generation and orchestrator system prompt at session start

**Why deferred:** Requires user accounts. Add immediately after account infrastructure is live.

---

## Chatbot Advisor

After the interview, user can ask follow-up questions: "What should I study before my next session?"
Reads the user's interview history to give personalized advice.

- Requires user accounts and stored session history
- Simpler than it sounds — just a Claude conversation with the transcript + scores injected as context
- This is a high-value feature that directly drives subscription conversion

**Why now:** One of the features locked behind paywall. Strong motivation to upgrade.

---

## Basic Progress Tracking

Minimal — not full dashboards yet.

- Show score trend across sessions for each scoring category (line graph or table)
- "You've done 5 interviews. Your Communication score has improved from 6.2 → 7.8."
- Requires stored session history (above)

**Why MVP2:** This is the primary thing that makes users come back. Without progress tracking,
each session feels isolated. With it, the product becomes a training program.
