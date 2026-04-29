import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id                          TEXT PRIMARY KEY,
            name                        TEXT NOT NULL,
            interviewer_persona         TEXT,
            hint_frequency              TEXT,                -- high / medium / medium_low / low
            hint_style                  TEXT,                -- JSON array
            signals_wrong_answer_via    TEXT,                -- JSON array
            says_answer_is_wrong_directly INTEGER DEFAULT 0, -- always false for real companies
            modifies_problem_mid_interview INTEGER DEFAULT 0,
            question_style              TEXT,                -- well_defined / underspecified
            wrong_answer_response       TEXT,
            move_on_threshold           TEXT,
            known_focus_areas           TEXT,                -- JSON array
            interview_style_tags        TEXT,                -- JSON array
            similar_companies           TEXT,                -- JSON array of IDs (ordered, top 10)
            coding_in_standard_rounds   INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS company_rounds (
            id                      TEXT PRIMARY KEY,
            company_id              TEXT NOT NULL,
            round_name              TEXT NOT NULL,           -- phone_screen / onsite_technical / etc.
            duration_minutes        INTEGER,
            question_count_range    TEXT,                    -- JSON [min, max]
            focus                   TEXT,
            is_technical_only       INTEGER DEFAULT 1,
            category_weights        TEXT,                    -- JSON {technical, coding, system_design, behavioral}
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );

        CREATE TABLE IF NOT EXISTS roles (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            level           TEXT,                            -- entry / mid / senior / staff
            similar_roles   TEXT,                            -- JSON array of IDs (ordered, top 10)
            tags            TEXT                             -- JSON array
        );

        CREATE TABLE IF NOT EXISTS questions (
            id              TEXT PRIMARY KEY,
            question_text   TEXT NOT NULL,
            answer_text     TEXT,
            company_id      TEXT,
            role_id         TEXT,
            round           TEXT,
            category        TEXT,                            -- technical / coding / system_design / behavioral
            quality_score   REAL,                            -- 0.0–1.0, set at ingestion
            difficulty_score REAL,                           -- starts NULL, updated from session data
            source_url      TEXT,
            scraped_at      TIMESTAMP,
            tags            TEXT,                            -- JSON array
            briefing        TEXT,                            -- JSON, generated once by Domain Expert at enrichment time
            is_active       INTEGER DEFAULT 1,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id                      TEXT PRIMARY KEY,
            company_id              TEXT,
            role_id                 TEXT,
            round                   TEXT,
            status                  TEXT DEFAULT 'in_progress', -- in_progress / paused / completed / abandoned
            started_at              TIMESTAMP,
            ended_at                TIMESTAMP,
            paused_at_question      INTEGER,
            question_ids            TEXT,                    -- JSON array, ordered
            question_briefings      TEXT,                    -- JSON {question_id: briefing_object}
            question_summaries      TEXT,                    -- JSON {question_id: "1-3 sentence summary"}
            question_transcripts    TEXT,                    -- JSON {question_id: full transcript}
            question_voice_stats    TEXT,                    -- JSON {question_id: {filler_count, filler_rate_per_min, wpm}}
            pseudocode              TEXT,                    -- JSON {question_id: pseudocode_text}
            audio_path_user         TEXT,                    -- local path to user mic audio
            audio_path_ai           TEXT,                    -- local path to AI TTS audio (mixed at replay)
            scores                  TEXT,                    -- JSON {technical_correctness, problem_solving, communication, voice}
            analysis                TEXT,                    -- JSON full domain expert output
            hints_given             TEXT,                    -- JSON {question_id: hint_count}
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );
    """)

    conn.commit()
    conn.close()
    print(f"[db] Initialized at {DATABASE_PATH}")


if __name__ == "__main__":
    init_db()
