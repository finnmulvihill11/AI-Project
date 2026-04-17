# prep — Frontend PRD

## Product Overview

**prep** is an AI-powered mock technical interview platform. Users select a company and role, complete a live voice-based interview with an AI interviewer, and receive a detailed performance analysis at the end. The goal is to make mock interviews feel as close to the real thing as possible.

**Finn's scope:** Frontend — all pages, navigation, UI, auth, payments, and integration points for Matthew's AI model.
**Matthew's scope:** AI interview orchestration, voice handling, question selection, scoring, and post-interview analysis.

---

## Brand

| | |
|---|---|
| **Name** | prep (always lowercase) |
| **Colors** | Yellow (`#F5C518`), Black (`#0A0A0A`), White (`#FFFFFF`) |
| **Tone** | Clean, serious, functional. Traditional but sleek. No gradients, no glowing UI, no AI startup clichés. Think Stripe or Linear — purposeful whitespace, clear typography, obvious navigation. |
| **Typography** | Geist Sans / Geist Mono (via `next/font/google`) |

---

## Tech Stack

| Layer | Choice | Status |
|---|---|---|
| Framework | Next.js 16.2.2 (TypeScript, App Router) | Done |
| Styling | Tailwind CSS v4 (config via `@theme` in globals.css) | Done |
| Auth | Clerk (`@clerk/nextjs` v7) | Done — sign up/in working, avatar in navbar |
| Payments | Stripe | Not started |
| Voice | Matthew's model handles voice | Placeholder UI built |
| Database | Supabase or Neon Postgres | Not started |
| Deployment | Vercel | Not started |

---

## User Flow

```
Landing page
  └── Sign up / Log in (Clerk)
        └── Interview Prep tab
              └── Company + Role selection page
                    └── Interview page (live voice + chat box)
                          └── Analysis page (Matthew's scoring output)

Homepage tabs:
  ├── Interview Prep   → company/role selection
  ├── My Performance   → personal history + progress tracking
  ├── About (dropdown) → How it works / Companies / The Team / Pricing
  └── [Auth state]     → Sign in / Sign up / Avatar (signed in)
```

---

## Monetization

- Every user must create an account
- Each account gets **one free interview** (any company, any role)
- After the free interview ends, user is prompted to upgrade to premium
- Premium = unlimited interviews (monthly subscription via Stripe)
- Free trial is enforced per account — not per session or device

---

## Pages

### 1. Homepage (`/`) — BUILT
The marketing and entry point page.

**Sections (top to bottom):**
- Navbar — logo left, nav links center, auth right
- Hero — `prep` wordmark (`text-7xl`), subheadline, yellow "Start practicing" CTA
- Logo ticker — scrolling SVG logos (Google, Meta, Apple, Stripe, Netflix, GitHub, Spotify, Airbnb, Uber, Shopify) — infinite marquee animation
- Stats row — 3 columns with dividers: `2,400+ Questions`, `3 Companies`, `~10 min Avg. interview`
- How it works — 3 numbered steps (01/02/03 in yellow mono font)
- CTA strip — grey background, black "Get started free" button
- Footer — `prep` wordmark left, `© 2026 prep` right

**Design notes:**
- White background, yellow accents on CTAs and step numbers
- Logo ticker items are muted grey (`fill-neutral-300`) — non-distracting

---

### 2. Interview Prep (`/prep`) — BUILT (placeholder)
Company and role selection. Starting point for every interview.

**Content:**
- Heading: "Choose your interview"
- Free trial badge (yellow, `You have 1 free interview remaining`)
- 3 company cards (Google, Amazon, Jane Street) with role dropdowns
- Yellow dot indicator on selected card
- "Start Interview" button — disabled until company + role selected, yellow when active
- Routes to `/interview/demo-session` (placeholder)

**TODO:**
- Pull roles from Finn's DB
- Create real session via API on start
- Show upgrade prompt if free trial used

---

### 3. Interview Page (`/interview/[sessionId]`) — BUILT (placeholder)
The live mock interview.

**Layout:**
- Full dark background (`#0a0a0a`) — only page with dark theme
- Top bar: company name, role, timer
- Left panel: pulsing yellow dot speaking indicator, message feed
- Right panel: code/notes textarea (monospace, transparent bg)
- Bottom bar: Mute button, End Interview button (red)
- Routes to `/analysis/demo-session` on end

**Integration points (Matthew's model — all stubbed):**
- Voice input/output
- Question delivery
- Session state

---

### 4. Analysis Page (`/analysis/[sessionId]`) — BUILT (mock data)
Post-interview performance review.

**Content:**
- Header: company · role · date
- Overall score (`7.5` in yellow, `text-6xl`)
- 3 category scores: Problem Solving, Communication, Technical Knowledge
- Strengths (yellow dots) and To improve (grey dots) side by side
- Question breakdown — each question with score and feedback
- CTAs: "Practice again" (yellow) → `/prep`, "View my performance →" (text)

**TODO:**
- Replace mock data with Matthew's API response
- Add paywall prompt/overlay for free trial users

---

### 5. My Performance (`/performance`) — BUILT (mock data)
Personal history and progress tracking.

**Content:**
- Stats row: Interviews count, Avg. score (yellow), Best score
- Bar chart: score over time (inline style height, yellow bars)
- Interview history table: Company, Role, Date, Score, View link → `/analysis/[id]`

**TODO:**
- Replace mock data with real DB queries
- Gate behind auth/premium

---

### 6. Auth Pages (`/sign-in`, `/sign-up`) — BUILT
Handled by Clerk with catch-all routes (`[[...rest]]`).

- `/sign-in/[[...rest]]/page.tsx` — renders `<SignIn />`
- `/sign-up/[[...rest]]/page.tsx` — renders `<SignUp />`
- Middleware protects: `/prep`, `/interview`, `/analysis`, `/performance`
- After sign-in → `/prep`, after sign-up → `/prep`
- Clerk dashboard: clerk.com (Finn's account)

**Navbar auth state:**
- Signed out: "Sign in" (text link) + "Sign up" (black button)
- Signed in: Black circle avatar with user initials, click to sign out

---

### 7. About (`/about`) — BUILT
Informational page, accessible via dropdown in navbar.

**Sections (each with anchor ID for dropdown deep-links):**
- `#how-it-works` — 3 numbered steps with detail
- `#companies` — card per company with type tags (Coding, System Design, etc.)
- `#team` — Finn (Data & Infrastructure) + Matthew (AI & Interview Engine)
- `#pricing` — Free tier card + Pro card ("Coming soon")

**Navbar dropdown items:**
- How it works → `/about#how-it-works`
- Companies → `/about#companies`
- The Team → `/about#team`
- Pricing → `/about#pricing`

---

## Navbar — BUILT

- **Left:** `prep` wordmark → `/`
- **Center nav:** Interview Prep, My Performance, About (dropdown)
- **Right:** Sign in / Sign up (signed out) or initials avatar (signed in)
- Hidden on `/interview/*` routes (full-focus interview mode)
- Sticky, `z-50`, white background, bottom border

---

## Free Trial Enforcement Logic (not yet built)

```
User signs up
  → free_interviews_used = 0 stored in DB

User starts interview
  → if free_interviews_used >= 1 AND not premium → show upgrade prompt, block start
  → if free_interviews_used == 0 OR is premium → allow start

Interview completes
  → if not premium → increment free_interviews_used = 1
  → show analysis page
  → show upgrade CTA on analysis page
```

---

## Integration Points with Matthew's Model

All placeholders in current MVP — stubbed with mock data.

| Feature | What Finn builds | What Matthew provides |
|---|---|---|
| Live interview | Voice UI, chat box, session layout | Voice handling, question delivery, session management |
| Analysis page | Page layout, data rendering | Scores, per-question feedback, overall summary |
| Role list | Dropdown populated from DB | N/A (comes from Finn's question data) |
| Performance history | Dashboard layout | Per-interview score data |

---

## MVP Checklist

| Item | Status |
|---|---|
| Homepage | Done |
| Auth (Clerk) | Done |
| Interview Prep page | Done (placeholder) |
| Interview page | Done (placeholder) |
| Analysis page | Done (mock data) |
| My Performance page | Done (mock data) |
| About page + dropdown | Done |
| Stripe integration | Not started |
| Wire up Matthew's voice API | Not started |
| Wire up real DB data | Not started |
| Vercel deployment | Not started |

---

## Open Items

| Item | Default used for now | To confirm |
|---|---|---|
| Companies on day 1 | Google, Amazon, Jane Street | Expand as scraper grows |
| Roles | Hardcoded | Pull from DB later |
| Interviewer speaking state | Pulsing yellow dot | Swap for waveform if preferred |
| Chat box | Simple textarea | Upgrade to Monaco editor if needed |
| Interview duration | No timer yet | Matthew's model decides |
| Matthew's scoring shape | Mock: overall (1-10) + 3 categories | Update when API ready |
| My Performance access | Open (mock) | Gate behind premium |
| Social login | Email/password only | Add Google/GitHub later |
| Subscription price | $20/month | TBD |
| Mobile | Desktop-first | Add responsiveness later |
| Team bios | Matthew's last name TBD | Update when confirmed |
