import av
import io
import json
import os
import asyncio
import random
import time
from datetime import datetime
from fastapi import WebSocket
import numpy as np
from database import get_connection
from orchestrator import build_system_prompt, get_interviewer_response
from stt import create_deepgram_connection, close_connection
from tts import synthesize_speech
from turn_detection import is_turn_complete, _load_model

# Filler words tracked for voice scoring (fed to Domain Expert)
FILLER_WORDS = {"um", "uh", "like", "literally", "basically", "actually", "you know"}

# Silence thresholds before AI prompts the candidate (per decisions-log.md)
SILENCE_THRESHOLD_VERBAL = (20, 30)   # randomized range in seconds
SILENCE_THRESHOLD_CODING  = (45, 60)  # longer — silence during coding is normal thinking

# webm container magic bytes (EBML header start).
# MediaRecorder's first chunk always begins with these four bytes.
# Subsequent chunks (Clusters) start with 0x1F 0x43 0xB6 0x75.
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


def _decode_webm_to_pcm(webm_init: bytes, chunks: list[bytes],
                         target_sr: int = 16000) -> np.ndarray:
    """
    Decode accumulated webm-opus chunks to mono float32 PCM at target_sr.

    webm_init is prepended so PyAV can parse the container format.  Without
    the EBML header + Tracks info from the init segment, PyAV cannot determine
    the codec or channel layout of the media-only Cluster chunks.

    Returns empty array on failure — callers fall back to the syntactic heuristic.
    """
    if not chunks or not webm_init:
        return np.array([], dtype=np.float32)
    try:
        data      = webm_init + b"".join(chunks)
        container = av.open(io.BytesIO(data))
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=target_sr)
        frames    = []
        for frame in container.decode(audio=0):
            for r in resampler.resample(frame):
                frames.append(r.to_ndarray()[0])
        for r in resampler.resample(None):
            frames.append(r.to_ndarray()[0])
        if not frames:
            return np.array([], dtype=np.float32)
        return np.concatenate(frames).astype(np.float32)
    except Exception as e:
        print(f"[interview_loop] audio decode error (non-fatal): {e}")
        return np.array([], dtype=np.float32)


async def _speak(websocket: WebSocket, ai_file, text: str):
    """
    Stream TTS audio to frontend and write to AI recording simultaneously.
    Sends ai_speaking_start / ai_speaking_end so frontend can gate the mic.
    """
    await websocket.send_json({"type": "ai_speaking_start"})
    async for chunk in synthesize_speech(text):
        ai_file.write(chunk)
        await websocket.send_bytes(chunk)
    await websocket.send_json({"type": "ai_speaking_end"})


async def _compress_transcript(conversation_history: list[dict],
                                question_text: str) -> str:
    """
    Compress a completed question's conversation to 1-3 sentences for orchestrator
    context. Uses Haiku — cheap, fast, clean summaries.
    e.g. "LRU Cache — correct O(1) approach, missed edge case, one hint, self-corrected."
    """
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    transcript_text = "\n".join(
        f"{t['role'].upper()}: {t['content']}" for t in conversation_history
    )
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=(
            "Summarize this interview question exchange in 1-3 sentences. "
            "Include: the topic, whether the candidate got it right, hints given, "
            "and any notable strengths or failures. Be terse — this is context for "
            "the next question, not a full review."
        ),
        messages=[{"role": "user",
                   "content": f"Question: {question_text}\n\n{transcript_text}"}],
    )
    return response.content[0].text.strip()


async def run_interview_loop(websocket: WebSocket, session_id: str):
    """
    Core interview loop. Runs for the duration of a live session.

    WebSocket protocol:
      Frontend → Backend (bytes):  raw webm-opus audio from MediaRecorder
      Frontend → Backend (JSON):   {"type": "pseudocode", "content": "..."}
                                   {"type": "end_interview"}
      Backend → Frontend (bytes):  AI TTS audio chunks
      Backend → Frontend (JSON):   {"type": "question_start", "question_index",
                                            "total_questions", "category"}
                                   {"type": "ai_speaking_start"}
                                   {"type": "ai_speaking_end"}
                                   {"type": "interview_complete"}
                                   {"type": "analysis_ready"}
                                   {"type": "error", "message": "..."}
    """

    # ── Load session ──────────────────────────────────────────────────────────

    conn = get_connection()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        conn.close()
        return
    session = dict(session)

    company        = conn.execute(
        "SELECT * FROM companies WHERE id = ?", (session["company_id"],)
    ).fetchone()
    question_ids   = json.loads(session["question_ids"])
    questions_rows = conn.execute(
        f"SELECT * FROM questions WHERE id IN ({','.join('?' * len(question_ids))})",
        question_ids,
    ).fetchall()
    conn.close()

    company_profile  = dict(company)
    questions_by_id  = {q["id"]: dict(q) for q in questions_rows}
    briefings        = json.loads(session["question_briefings"])
    session_context  = {"role": session["role_id"], "round": session["round"]}

    # Accumulators written to DB at session end
    all_transcripts = {}
    all_voice_stats = {}
    all_hints       = {}
    past_summaries  = []    # 1-3 sentence summaries of completed questions

    # Audio recording — open once, kept for entire session
    audio_storage   = os.getenv("AUDIO_STORAGE_PATH")
    audio_path_user = f"{audio_storage}/{session_id}_user.webm"
    audio_path_ai   = f"{audio_storage}/{session_id}_ai.webm"
    user_file = open(audio_path_user, "wb")
    ai_file   = open(audio_path_ai,   "wb")

    # End-of-session signal (set when user clicks "End Interview")
    end_event = asyncio.Event()

    # ── webm init segment ─────────────────────────────────────────────────────
    # MediaRecorder's very first chunk contains the EBML header + Tracks element
    # (codec, channels, sample rate). All subsequent chunks are raw Clusters and
    # CANNOT be decoded without this init segment. We capture it once here and
    # prepend it to every decode call throughout the session.
    #
    # Detection: EBML magic = 0x1A 0x45 0xDF 0xA3. On MediaRecorder restart
    # (e.g. question boundary on some frontends) a new init segment arrives and
    # we update the saved copy so decoding always uses the correct codec info.
    webm_init: bytes = b""

    # ── Pre-warm Smart Turn model ─────────────────────────────────────────────
    # _load_model() downloads 8 MB from HuggingFace on first call. Running it
    # now (before the first question) ensures the model is in memory before any
    # speech_final fires. Without this, the first on_utterance_end call would
    # block in the executor for 5-30s depending on network, silently dropping
    # all speech_final events during that window.
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _load_model)

    try:
        # ── Question loop ─────────────────────────────────────────────────────

        for q_index, q_id in enumerate(question_ids):
            if end_event.is_set():
                break

            question  = questions_by_id[q_id]
            briefing  = briefings.get(q_id, {"question": question["question_text"]})
            category  = question.get("category", "technical")
            is_coding = (category == "coding")

            await websocket.send_json({
                "type":            "question_start",
                "question_index":  q_index,
                "total_questions": len(question_ids),
                "category":        category,
            })

            system_prompt = build_system_prompt(
                company_profile=company_profile,
                question_briefing=briefing,
                past_question_summaries=past_summaries,
                session_context=session_context,
            )

            # ── Per-question state ────────────────────────────────────────────

            conversation_history = []
            current_pseudocode   = ""
            hints_this_question  = 0
            move_on              = False

            # ai_speaking: True from the moment speak_and_wait starts until the
            # frontend sends audio_done (after playback finishes).
            # on_utterance_end does NOT drop speech when True — it saves transcripts
            # to suppressed_transcript so they are recovered after audio_done.
            ai_speaking      = False
            audio_done_event = asyncio.Event()
            utterance_queue  = asyncio.Queue()

            # tts_active: True only while _speak() is actively streaming TTS chunks
            # to the frontend.  audio_buffer gates on (not tts_active) so user audio
            # is collected from the moment streaming ends — even though the frontend
            # hasn't finished playing yet.  This is separate from ai_speaking so we
            # can buffer early without risking echo from our own streaming audio.
            tts_active: bool = False

            # suppressed_transcript: transcripts from Deepgram speech_final events
            # that fired while ai_speaking=True (i.e. during frontend audio playback).
            # Instead of dropping them, on_utterance_end accumulates them here.
            # speak_and_wait processes them immediately after audio_done fires.
            suppressed_transcript: str = ""

            # audio_buffer: raw webm Cluster chunks from the frontend since the
            # last AI response. Decoded to PCM and fed to Smart Turn.
            # Cleared at the START of each speak_and_wait call (before speaking).
            audio_buffer: list[bytes] = []

            # utterance_parts: is_final transcript segments accumulated across
            # consecutive speech_final events when Smart Turn says "incomplete".
            # Smart Turn keeps saying "wait" while the user pauses mid-thought;
            # parts accumulate until it says "complete", at which point the full
            # joined text is sent to the AI. Cleared in speak_and_wait.
            utterance_parts: list[str] = []

            # st_processing: prevents concurrent Smart Turn runs if two
            # speech_final events arrive before the first finishes processing.
            st_processing = False

            # turn_responded: set when we put a transcript in the queue.
            # Prevents a second speech_final from queuing a duplicate before the
            # AI has started speaking and ai_speaking becomes True.
            # Reset at the start of each speak_and_wait call.
            turn_responded = False

            # Voice stats
            filler_count = 0
            word_count   = 0
            q_start_time = time.time()

            # ── AI opens the question ─────────────────────────────────────────
            # Opening speech is delivered inside process_utterances via
            # speak_and_wait so it uses the same tts_active / ai_speaking /
            # suppressed_transcript state machine as every subsequent AI turn.

            opening_response, _, _ = await get_interviewer_response(
                [{"role": "user", "content": "[START]"}],
                system_prompt,
            )
            conversation_history.append({"role": "assistant",
                                         "content": opening_response})

            # ── Deepgram callbacks ────────────────────────────────────────────

            async def on_transcript(text: str):
                nonlocal filler_count, word_count
                words         = text.lower().split()
                word_count   += len(words)
                filler_count += sum(1 for w in words if w in FILLER_WORDS)

            async def on_utterance_end(segment_transcript: str):
                """
                Called by stt.py each time Deepgram fires speech_final (300ms
                silence) or the utterance_end_ms fallback.

                If ai_speaking (frontend audio still playing): save the transcript
                to suppressed_transcript instead of dropping it.  speak_and_wait
                processes suppressed_transcript after audio_done so answers given
                during playback are never silently lost.

                Otherwise: accumulate into utterance_parts and run Smart Turn via
                _run_turn_detection.  If complete, queue for AI response.  If not,
                keep accumulating — next speech_final adds more audio + text.
                """
                nonlocal suppressed_transcript

                if turn_responded:
                    return
                if ai_speaking:
                    # Save rather than drop — recovered in speak_and_wait.
                    suppressed_transcript = (
                        suppressed_transcript + " " + segment_transcript
                    ).strip()
                    return
                if st_processing:
                    return

                utterance_parts.append(segment_transcript)
                await _run_turn_detection(" ".join(utterance_parts).strip())

            async def _run_turn_detection(full_transcript: str) -> None:
                """
                Run Smart Turn + LiveKit turn-detector on the current
                audio_buffer + full_transcript. If both agree the turn is
                complete, set turn_responded and queue the transcript.

                Called from on_utterance_end (normal Deepgram path) and from
                speak_and_wait after audio_done (suppressed-transcript recovery).
                Guards against concurrent runs (st_processing) and double-queuing
                (turn_responded).
                """
                nonlocal st_processing, turn_responded
                if st_processing or turn_responded:
                    return
                st_processing = True
                try:
                    pcm = _decode_webm_to_pcm(webm_init, list(audio_buffer))

                    # Pass the last AI turn so LiveKit's LM has conversation
                    # context. Without it LK outputs near-zero for all inputs
                    # and cannot discriminate complete vs. mid-sentence.
                    last_ai = ""
                    ai_turns = [t for t in conversation_history
                                if t["role"] == "assistant"]
                    if ai_turns:
                        last_ai = ai_turns[-1]["content"]

                    done = await is_turn_complete(pcm, full_transcript, last_ai)
                    if done:
                        turn_responded = True
                        audio_buffer.clear()
                        utterance_parts.clear()
                        await utterance_queue.put(full_transcript)
                    # else: utterance_parts and audio_buffer intact;
                    # next speech_final appends more before retrying.
                except Exception as e:
                    print(f"[interview] _run_turn_detection ERROR: {type(e).__name__}: {e}")
                    import traceback; traceback.print_exc()
                finally:
                    st_processing = False

            deepgram_conn = await create_deepgram_connection(
                on_transcript, on_utterance_end
            )

            # Silence timer — nudges the candidate if silent too long
            silence_range = SILENCE_THRESHOLD_CODING if is_coding \
                else SILENCE_THRESHOLD_VERBAL
            silence_task = None

            def reset_silence_timer():
                nonlocal silence_task
                if silence_task and not silence_task.done():
                    silence_task.cancel()
                silence_task = asyncio.create_task(_silence_nudge(
                    random.randint(*silence_range), utterance_queue,
                ))

            # ── Concurrent tasks ──────────────────────────────────────────────

            async def receive_audio():
                """
                Read WebSocket messages and forward audio to Deepgram.

                Webm init segment handling:
                  The first chunk from MediaRecorder always starts with EBML magic
                  bytes and contains the container header.  We save it to webm_init
                  (session-level) so that every subsequent decode call can prepend
                  it.  Init chunks are NOT added to audio_buffer — they act as a
                  persistent header only.

                  On MediaRecorder restart (some frontends do this per-question) a
                  new EBML header arrives; we update webm_init so the codec info
                  stays current.

                Audio buffering gates on tts_active (not ai_speaking): chunks are
                collected once TTS streaming ends, even while the frontend is still
                playing the audio.  This ensures user speech during playback is
                captured for Smart Turn, avoiding the old drop window.
                """
                nonlocal current_pseudocode, webm_init

                while not move_on and not end_event.is_set():
                    try:
                        msg = await asyncio.wait_for(
                            websocket.receive(), timeout=0.5
                        )

                        if msg.get("bytes"):
                            chunk = msg["bytes"]
                            user_file.write(chunk)
                            await deepgram_conn.send(chunk)

                            if chunk[:4] == WEBM_MAGIC:
                                # Init segment — save/update, never add to buffer
                                webm_init = chunk
                            elif not tts_active:
                                # Buffer once TTS streaming ends (not ai_speaking)
                                # so user speech during frontend playback is captured.
                                audio_buffer.append(chunk)

                        elif msg.get("text"):
                            data = json.loads(msg["text"])
                            if data["type"] == "pseudocode":
                                current_pseudocode = data.get("content", "")
                            elif data["type"] == "end_interview":
                                end_event.set()
                            elif data["type"] == "audio_done":
                                audio_done_event.set()

                    except asyncio.TimeoutError:
                        pass
                    except RuntimeError:
                        end_event.set()     # client disconnected
                        break
                    except Exception as e:
                        print(f"[warn] receive_audio: {type(e).__name__}: {e}")
                        end_event.set()
                        break

            def drain_queue():
                """Discard queued items accumulated while AI was speaking."""
                while not utterance_queue.empty():
                    utterance_queue.get_nowait()

            async def speak_and_wait(text: str):
                """
                Stream TTS to the frontend, then block until the frontend signals
                playback is finished (audio_done JSON message, 15s failsafe).

                State transitions:
                  1. Clear stale state from the previous turn upfront — buffer,
                     accumulated parts, responded flag, and queued items.
                  2. tts_active=True during _speak(): audio_buffer does NOT collect
                     (avoids buffering our own echo). ai_speaking=True blocks
                     on_utterance_end from processing (but not from saving).
                  3. After _speak() returns: tts_active=False → audio_buffer starts
                     collecting user speech immediately, before frontend finishes
                     playing. suppressed_transcript reset so only speech from this
                     playback window is recovered (not noise during streaming).
                  4. After audio_done: ai_speaking=False → on_utterance_end resumes.
                  5. If speech_final fired during playback, suppressed_transcript
                     holds the transcript. Process it now via _run_turn_detection
                     using the audio collected since tts_active went False.
                """
                nonlocal ai_speaking, turn_responded, tts_active, suppressed_transcript

                # ── Reset state for this AI turn ──────────────────────────────
                audio_done_event.clear()
                audio_buffer.clear()       # discard previous turn's buffered audio
                utterance_parts.clear()    # discard incomplete accumulation
                turn_responded = False
                drain_queue()

                # ── Stream TTS ────────────────────────────────────────────────
                ai_speaking = True
                tts_active  = True
                await _speak(websocket, ai_file, text)
                tts_active  = False
                # Start fresh: discard any spurious transcripts that fired during
                # streaming (background noise, echo). Only capture from here on.
                suppressed_transcript = ""

                # ── Wait for frontend playback to finish ──────────────────────
                try:
                    await asyncio.wait_for(audio_done_event.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    pass

                ai_speaking = False
                reset_silence_timer()

                # ── Recover suppressed speech ─────────────────────────────────
                # speech_final events that arrived while ai_speaking=True saved
                # transcripts to suppressed_transcript instead of being dropped.
                # audio_buffer has the matching audio (collected since tts_active
                # went False). Run Smart Turn now so the user's answer is not lost.
                if suppressed_transcript and not turn_responded:
                    utterance_parts.append(suppressed_transcript)
                    suppressed_transcript = ""
                    await _run_turn_detection(" ".join(utterance_parts).strip())

            async def process_utterances():
                """
                Deliver the opening question then loop: dequeue transcripts,
                call Haiku, speak response.  All AI speech goes through
                speak_and_wait which owns the tts_active / ai_speaking /
                suppressed_transcript state machine uniformly — opening speech
                is no different from any follow-up response.
                """
                nonlocal hints_this_question, move_on

                await speak_and_wait(opening_response)

                while not move_on and not end_event.is_set():
                    try:
                        transcript = await asyncio.wait_for(
                            utterance_queue.get(), timeout=0.5
                        )
                    except asyncio.TimeoutError:
                        continue

                    if transcript == "[SILENCE]":
                        # Candidate has been silent — gently prompt.
                        # Do NOT add to conversation_history; the nudge is
                        # invisible to the AI's context for the next real turn.
                        silence_messages = conversation_history + [{
                            "role":    "user",
                            "content": "[The candidate has been silent. "
                                       "Gently prompt them — one sentence only.]",
                        }]
                        response_text, _, _ = await get_interviewer_response(
                            silence_messages, system_prompt
                        )
                        await speak_and_wait(response_text)
                        continue

                    conversation_history.append({
                        "role": "user", "content": transcript
                    })
                    response_text, hint_given, should_move_on = \
                        await get_interviewer_response(
                            conversation_history,
                            system_prompt,
                            current_pseudocode if is_coding else None,
                        )

                    if hint_given:
                        hints_this_question += 1

                    conversation_history.append({
                        "role": "assistant", "content": response_text
                    })
                    await speak_and_wait(response_text)

                    if should_move_on:
                        move_on = True

            await asyncio.gather(receive_audio(), process_utterances())

            if silence_task and not silence_task.done():
                silence_task.cancel()

            await close_connection(deepgram_conn)

            # ── Save question data ────────────────────────────────────────────

            elapsed_minutes = (time.time() - q_start_time) / 60
            all_transcripts[q_id] = [
                t for t in conversation_history if t["role"] == "user"
            ]
            all_voice_stats[q_id] = {
                "filler_count":        filler_count,
                "filler_rate_per_min": round(filler_count / elapsed_minutes, 2)
                                       if elapsed_minutes > 0 else 0,
                "wpm":                 round(word_count / elapsed_minutes, 1)
                                       if elapsed_minutes > 0 else 0,
            }
            all_hints[q_id] = hints_this_question

            if conversation_history:
                summary = await _compress_transcript(
                    conversation_history, question["question_text"]
                )
                past_summaries.append(summary)

        # ── Interview complete ────────────────────────────────────────────────

        await websocket.send_json({"type": "interview_complete"})

        now  = datetime.utcnow().isoformat()
        conn = get_connection()
        conn.execute("""
            UPDATE sessions SET
                status = 'completed',
                ended_at = ?,
                question_transcripts = ?,
                question_voice_stats = ?,
                hints_given = ?,
                audio_path_user = ?,
                audio_path_ai = ?
            WHERE id = ?
        """, (
            now,
            json.dumps(all_transcripts),
            json.dumps(all_voice_stats),
            json.dumps(all_hints),
            audio_path_user,
            audio_path_ai,
            session_id,
        ))
        conn.commit()

        from domain_expert import score_session
        result = await score_session(
            session         = dict(conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()),
            questions       = list(questions_by_id.values()),
            company_profile = company_profile,
        )
        conn.close()
        conn = get_connection()
        conn.execute(
            "UPDATE sessions SET scores = ?, analysis = ? WHERE id = ?",
            (json.dumps(result["scores"]), json.dumps(result["analysis"]),
             session_id),
        )
        conn.commit()
        conn.close()
        await websocket.send_json({"type": "analysis_ready"})

    finally:
        user_file.close()
        ai_file.close()


async def _silence_nudge(threshold_seconds: int, utterance_queue: asyncio.Queue):
    """
    Sleep threshold_seconds, then send a sentinel that process_utterances
    interprets as "candidate has been silent" — triggers a gentle prompt.
    Cancelled and restarted by reset_silence_timer on every AI response.
    """
    await asyncio.sleep(threshold_seconds)
    await utterance_queue.put("[SILENCE]")
