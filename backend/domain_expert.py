import os
import json
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def generate_briefing(question: dict, company_profile: dict) -> dict:
    """
    ENRICHMENT PIPELINE FUNCTION — called once per question by Finn's pipeline at ingestion.
    NOT called at session start. Result stored to questions.briefing in the DB.

    Generates a Domain Expert briefing for a single question calibrated to the
    company's interview style. Tells the orchestrator (Haiku) what a good answer
    looks like, what wrong paths to watch for, and what hints to give.

    Output schema (stored as JSON in questions.briefing):
    {
        "question": str,
        "category": str,
        "ideal_answer_summary": str,
        "key_concepts": [str],
        "common_wrong_paths": [{"path": str, "signal": str, "response": str}],
        "good_signals": [str],
        "hint_if_stuck": str,
        "triggers_coding_tab": bool
    }
    """
    company_name    = company_profile.get("name", "a tech company")
    hint_frequency  = company_profile.get("hint_frequency", "medium")
    hint_style      = json.loads(company_profile.get("hint_style", "[]"))
    question_text   = question.get("question_text", "")
    answer_text     = question.get("answer_text", "")
    category        = question.get("category", "technical")

    answer_block = f"\n\nReference answer (if available):\n{answer_text}" if answer_text else ""

    prompt = f"""You are preparing a briefing for an AI interviewer at {company_name}.
The interviewer will use this briefing to evaluate a candidate in real time.

Question: {question_text}{answer_block}
Category: {category}
Company hint style: {hint_frequency} frequency, style: {', '.join(hint_style) if hint_style else 'standard'}

Generate a briefing JSON with exactly these fields:
{{
  "question": "<the question text>",
  "category": "<category>",
  "triggers_coding_tab": <true if candidate needs to write code, false otherwise>,
  "ideal_answer_summary": "<2-4 sentences covering what a strong answer includes>",
  "key_concepts": ["<concept 1>", "<concept 2>", ...],
  "common_wrong_paths": [
    {{
      "path": "<description of wrong approach>",
      "signal": "<what the candidate says that signals this wrong path>",
      "response": "<exact probe or redirect the interviewer should give>"
    }}
  ],
  "good_signals": ["<thing to listen for that indicates a strong candidate>", ...],
  "hint_if_stuck": "<a single hint calibrated to {company_name}'s hint style to give if candidate is stuck>"
}}

Return only valid JSON. No explanation, no markdown."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def score_session(
    session: dict,
    questions: list[dict],
    company_profile: dict,
) -> dict:
    """
    Called once after all questions are complete. Runs during the analysis loading screen.
    Claude Sonnet scores the full session and produces the results the user sees.

    Returns:
    {
        "scores": {
            "technical_correctness": float,  # 0-10
            "problem_solving":       float,
            "communication":         float,
            "voice":                 float
        },
        "analysis": {
            "overall_feedback":       str,
            "study_recommendations":  [str],
            "per_question": {
                "<question_id>": {
                    "score":      float,
                    "strengths":  [str],
                    "weaknesses": [str],
                    "flags":      [str],
                    "feedback":   str
                }
            }
        }
    }
    """
    company_name     = company_profile.get("name", "the company")
    transcripts      = json.loads(session.get("question_transcripts", "{}"))
    voice_stats_all  = json.loads(session.get("question_voice_stats",  "{}"))
    hints_given_all  = json.loads(session.get("hints_given",           "{}"))
    pseudocode_all   = json.loads(session.get("pseudocode",            "{}"))
    briefings        = json.loads(session.get("question_briefings",    "{}"))

    # Build a per-question block for the scoring prompt
    question_blocks = []
    for q in questions:
        q_id         = q["id"]
        transcript   = transcripts.get(q_id, [])
        voice_stats  = voice_stats_all.get(q_id, {})
        hints        = hints_given_all.get(q_id, 0)
        pseudocode   = pseudocode_all.get(q_id, "")
        briefing     = briefings.get(q_id, {})

        transcript_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}"
            for t in transcript
        ) if transcript else "(no transcript recorded)"

        pseudocode_block = f"\nCandidate pseudocode:\n{pseudocode}" if pseudocode else ""

        block = f"""
--- QUESTION {q_id} ---
Question: {q.get('question_text', '')}
Category: {q.get('category', 'technical')}
Ideal answer: {briefing.get('ideal_answer_summary', 'N/A')}
Key concepts expected: {', '.join(briefing.get('key_concepts', []))}
Hints given: {hints}

Transcript:
{transcript_text}{pseudocode_block}

Voice stats:
- Filler words: {voice_stats.get('filler_count', 0)} ({voice_stats.get('filler_rate_per_min', 0)} per min)
- Speaking rate: {voice_stats.get('wpm', 0)} WPM
"""
        question_blocks.append(block)

    all_questions_text = "\n".join(question_blocks)

    prompt = f"""You are a senior technical interviewer at {company_name} scoring a candidate's mock interview.

{all_questions_text}

Score the candidate across four categories, each out of 10.0 with one decimal place:
- technical_correctness: Did they get the right answer? Penalize for hints needed.
- problem_solving: Quality of their approach, how they broke down the problem, adaptability.
- communication: Clarity of explanation, structure, conciseness, avoiding over/under-explaining.
- voice: Filler word rate, speaking pace (ideal ~130-160 WPM), clarity. Use the voice stats above.

Return a JSON object with exactly this structure:
{{
  "scores": {{
    "technical_correctness": <float>,
    "problem_solving":       <float>,
    "communication":         <float>,
    "voice":                 <float>
  }},
  "analysis": {{
    "overall_feedback": "<2-4 sentences summarizing overall performance>",
    "study_recommendations": ["<specific thing to study or practice>", ...],
    "per_question": {{
      "<question_id>": {{
        "score":      <float 0-10>,
        "strengths":  ["<specific thing they did well>", ...],
        "weaknesses": ["<specific gap or miss>", ...],
        "flags":      ["<notable issue — excessive fillers, long silence, gave up, etc.>"],
        "feedback":   "<2-3 sentences of direct, actionable coaching>"
      }}
    }}
  }}
}}

Be direct and specific. Vague feedback ("good communication") is useless.
Return only valid JSON. No explanation, no markdown."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())
