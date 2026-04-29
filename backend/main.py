import json
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import get_connection, init_db
from question_selector import select_questions
from mock_data import (
    MOCK_COMPANIES, MOCK_ROUNDS, MOCK_ROLES,
    get_mock_company_profile, get_mock_questions,
)

load_dotenv()

app = FastAPI(title="Interview App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "null"],  # Next.js + file:// test page
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@app.get("/companies")
async def get_companies():
    """List all companies. Used to populate the company selection screen."""
    # TODO: switch to DB query once companies table is seeded:
    #   rows = conn.execute("SELECT id, name, interview_style_tags, known_focus_areas FROM companies").fetchall()
    #   return [dict(r) for r in rows]
    return MOCK_COMPANIES


@app.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Full company profile. Used by Company Explorer detail page."""
    # TODO: switch to DB query once companies table is seeded:
    #   row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    #   if not row: raise HTTPException(404)
    #   return dict(row)
    return get_mock_company_profile(company_id)


@app.get("/companies/{company_id}/rounds")
async def get_company_rounds(company_id: str):
    """Rounds available for a company. Used by the round selection screen."""
    # TODO: switch to DB query once company_rounds table is seeded:
    #   rows = conn.execute("SELECT * FROM company_rounds WHERE company_id = ?", (company_id,)).fetchall()
    #   return [dict(r) for r in rows]
    return MOCK_ROUNDS


@app.get("/companies/{company_id}/roles")
async def get_company_roles(company_id: str):
    """Roles that have at least one active question for this company."""
    # TODO: switch to DB query once questions table is seeded:
    #   rows = conn.execute("""
    #       SELECT DISTINCT r.* FROM roles r
    #       JOIN questions q ON q.role_id = r.id
    #       WHERE q.company_id = ? AND q.is_active = 1
    #   """, (company_id,)).fetchall()
    #   return [dict(r) for r in rows]
    return MOCK_ROLES


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.post("/sessions")
async def create_session(body: dict):
    """
    Create a session. Called when user hits the waiting room screen.
    Runs question selection + domain expert briefing generation.
    Returns session_id so the frontend can open the WebSocket.
    """
    company_id = body.get("company_id")
    role_id = body.get("role_id")
    round_name = body.get("round")

    if not all([company_id, role_id, round_name]):
        raise HTTPException(status_code=400, detail="company_id, role_id, and round are required")

    # TODO: once DB is seeded, replace the mock block below with real DB queries:
    #
    #   questions = select_questions(company_id, role_id, round_name)
    #   conn = get_connection()
    #   company = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    #   conn.close()
    #   if not company: raise HTTPException(404)
    #   company_profile = dict(company)
    #   briefings = {}
    #   for q in questions:
    #       briefings[q["id"]] = json.loads(q["briefing"]) if q.get("briefing") else {"question": q["question_text"]}
    #   summaries = {q["id"]: q["question_text"][:200] for q in questions}

    # ── Mock data path (MVP — no DB questions yet) ────────────────────────────
    questions       = get_mock_questions(n=2)
    question_ids    = [q["id"] for q in questions]
    company_profile = get_mock_company_profile(company_id)
    briefings       = {q["id"]: json.loads(q["briefing"]) for q in questions}
    summaries       = {q["id"]: q["question_text"][:200] for q in questions}

    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    conn.execute("""
        INSERT INTO sessions (
            id, company_id, role_id, round, status, started_at,
            question_ids, question_briefings, question_summaries,
            question_transcripts, question_voice_stats, pseudocode,
            hints_given
        ) VALUES (?, ?, ?, ?, 'in_progress', ?, ?, ?, ?, '{}', '{}', '{}', '{}')
    """, (
        session_id, company_id, role_id, round_name, now,
        json.dumps(question_ids),
        json.dumps(briefings),
        json.dumps(summaries),
    ))
    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "question_count": len(questions),
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


@app.patch("/sessions/{session_id}/pause")
async def pause_session(session_id: str, body: dict):
    """Pause a session at a specific question index."""
    paused_at = body.get("paused_at_question", 0)
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET status = 'paused', paused_at_question = ? WHERE id = ?",
        (paused_at, session_id)
    )
    conn.commit()
    conn.close()
    return {"status": "paused"}


@app.get("/sessions/{session_id}/analysis")
async def get_analysis(session_id: str):
    """Get post-interview scores and analysis. Only available after session is completed."""
    conn = get_connection()
    row = conn.execute("SELECT status, scores, analysis FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row["status"] != "completed":
        raise HTTPException(status_code=400, detail="Session not yet completed")
    return {
        "scores": json.loads(row["scores"] or "{}"),
        "analysis": json.loads(row["analysis"] or "{}"),
    }


# ---------------------------------------------------------------------------
# Live Interview WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: str):
    """
    Live interview loop.
    Frontend streams mic audio → backend → Deepgram STT → Haiku → ElevenLabs TTS → audio back.
    See interview_loop.py for full implementation.
    """
    from interview_loop import run_interview_loop
    await websocket.accept()
    try:
        await run_interview_loop(websocket, session_id)
    except WebSocketDisconnect:
        # Mark abandoned if user disconnects mid-session
        conn = get_connection()
        row = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row and row["status"] == "in_progress":
            conn.execute(
                "UPDATE sessions SET status = 'abandoned' WHERE id = ?", (session_id,)
            )
            conn.commit()
        conn.close()
