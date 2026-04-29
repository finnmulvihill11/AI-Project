import asyncio
from functools import lru_cache

import numpy as np
from huggingface_hub import hf_hub_download
from transformers import WhisperFeatureExtractor, AutoTokenizer
import onnxruntime as ort

# ── Smart Turn v3  (pipecat-ai/smart-turn-v3) ────────────────────────────────
# Whisper-Tiny encoder + binary classifier.
# Predicts P(turn complete) from raw PCM audio captured since the last AI
# response. Input: float32 mono 16kHz PCM up to 8 seconds, front-padded so
# speech sits at the END of the window. Output: sigmoid in [0, 1].
#
# Runs AFTER Deepgram speech_final (silence detected). Silence is already
# partial evidence of completion; the model distinguishes mid-thought pauses
# from genuine turn ends using prosody / energy patterns.

ST_REPO      = "pipecat-ai/smart-turn-v3"
ST_FILE      = "smart-turn-v3.2-cpu.onnx"
SAMPLE_RATE  = 16000
MAX_SAMPLES  = 8 * SAMPLE_RATE   # 128 000 samples = 8 seconds
MIN_AUDIO_SAMPLES = SAMPLE_RATE  # < 1 s → prosodic model unreliable, skip it

# ── LiveKit turn-detector  (livekit/turn-detector) ───────────────────────────
# SmolLM2-135M causal LM fine-tuned on conversations.
# Used as a VETO: if P(next token == <|im_end|>) is very low the utterance is
# structurally mid-sentence and we block regardless of what Smart Turn says.
#
# Requires conversation context to work correctly — without the preceding
# assistant turn P values are near-zero even for complete utterances.
# Input format: <|im_start|><|assistant|>{question}<|im_end|>
#               <|im_start|><|user|>{transcript}   ← no closing tag
# Output: logits[0, -1, vocab] → softmax → P(token_id=2) = P(<|im_end|>).
#
# Calibration (from empirical testing with interview speech):
#   True mid-sentence (trailing "and", "because", "So the way I would…"):
#       P ≈ 0.0000 – 0.0002
#   All complete turns (short, long, question-ending):
#       P ≥ 0.0143
#   → Veto threshold 0.003 sits cleanly between the two populations.
#   LiveKit DOES NOT trigger responses on its own; it only vetoes Smart Turn.

LK_REPO      = "livekit/turn-detector"
LK_FILE      = "model_quantized.onnx"
LK_EOU_ID    = 2     # <|im_end|> token id

# ── Decision thresholds ───────────────────────────────────────────────────────
ST_THRESHOLD = 0.65   # Smart Turn: raised from 0.5 → reduces prosodic false positives
LK_VETO      = 0.003  # LiveKit: below this = structurally mid-sentence → BLOCK

# ── Heuristic fallback ────────────────────────────────────────────────────────
# Used when audio is too short for Smart Turn (< 1 s) as a safety net.
# These words make a grammatically complete sentence impossible.
# Kept small: false blocks are worse than false triggers.
_MID_SENTENCE_ENDINGS = frozenset({
    "and", "but", "or", "yet", "nor",
    "because", "although", "though", "since", "while",
    "if", "unless", "until",
    "the", "a", "an",
    "to",
    "would", "could", "should", "will", "can", "may", "might", "must",
    "i",
    "then",
})


def _is_mid_sentence(transcript: str) -> bool:
    cleaned = transcript.strip().rstrip(".,!?;:")
    if not cleaned:
        return True
    return cleaned.split()[-1].lower() in _MID_SENTENCE_ENDINGS


# ── Model loaders (cached) ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_smart_turn():
    print("[turn_detection] Loading Smart Turn v3...")
    model_path = hf_hub_download(ST_REPO, ST_FILE)
    so = ort.SessionOptions()
    so.execution_mode           = ort.ExecutionMode.ORT_SEQUENTIAL
    so.inter_op_num_threads     = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session   = ort.InferenceSession(model_path, sess_options=so)
    extractor = WhisperFeatureExtractor(chunk_length=8)
    print("[turn_detection] Smart Turn v3 ready.")
    return session, extractor


@lru_cache(maxsize=1)
def _load_livekit_td():
    print("[turn_detection] Loading LiveKit turn-detector...")
    model_path = hf_hub_download(LK_REPO, LK_FILE)
    so = ort.SessionOptions()
    so.execution_mode           = ort.ExecutionMode.ORT_SEQUENTIAL
    so.inter_op_num_threads     = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session   = ort.InferenceSession(model_path, sess_options=so)
    tokenizer = AutoTokenizer.from_pretrained(LK_REPO)
    print("[turn_detection] LiveKit turn-detector ready.")
    return session, tokenizer


def _load_model():
    """
    Pre-warm both models. Called from interview_loop.py before the first
    question so neither download/load blocks on_utterance_end at runtime.
    """
    _load_smart_turn()
    _load_livekit_td()


# ── Synchronous inference (thread-pool safe) ──────────────────────────────────

def _predict_smart_turn_sync(session, extractor, audio: np.ndarray) -> float:
    """Smart Turn v3 inference. Returns sigmoid P(turn complete) in [0, 1]."""
    if len(audio) > MAX_SAMPLES:
        audio = audio[-MAX_SAMPLES:]
    elif len(audio) < MAX_SAMPLES:
        audio = np.pad(audio, (MAX_SAMPLES - len(audio), 0), mode="constant")

    inputs = extractor(
        audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors="np",
        padding="max_length",
        max_length=MAX_SAMPLES,
        truncation=True,
        do_normalize=True,
    )
    feats   = inputs.input_features.squeeze(0).astype(np.float32)[np.newaxis]
    outputs = session.run(None, {"input_features": feats})
    return float(outputs[0][0][0])


def _predict_livekit_sync(session, tokenizer,
                          transcript: str, last_assistant_turn: str) -> float:
    """
    LiveKit turn-detector inference. Returns P(next token == <|im_end|>).

    Format: <|im_start|><|assistant|>{last_assistant_turn}<|im_end|>
            <|im_start|><|user|>{transcript}
    No closing tag on the user turn — the model predicts whether it comes next.

    last_assistant_turn provides the conversation context the model needs.
    Without it the model treats this as generic text and P values are near-zero
    for all inputs, making it useless as a discriminator.
    """
    if last_assistant_turn:
        prompt = (
            f"<|im_start|><|assistant|>{last_assistant_turn}<|im_end|>"
            f"<|im_start|><|user|>{transcript}"
        )
    else:
        prompt = f"<|im_start|><|user|>{transcript}"

    input_ids = tokenizer(
        prompt,
        return_tensors="np",
        truncation=True,
        max_length=512,
    )["input_ids"].astype(np.int64)

    outputs = session.run(None, {"input_ids": input_ids})
    logits  = outputs[0][0, -1, :].astype(np.float64)
    logits -= logits.max()
    probs   = np.exp(logits)
    probs  /= probs.sum()
    return float(probs[LK_EOU_ID])


# ── Public API ────────────────────────────────────────────────────────────────

async def is_turn_complete(audio: np.ndarray, transcript: str,
                           last_assistant_turn: str = "") -> bool:
    """
    Decide whether the AI should respond now.

    audio:               float32 mono 16kHz PCM. All user speech since the last
                         AI response, decoded from the raw webm stream.
    transcript:          full accumulated text since the last AI response.
    last_assistant_turn: the AI's most recent question/response. Passed to the
                         LiveKit model for conversation context. Empty string
                         degrades LK to near-zero output (safe — it won't veto).

    Decision logic:
      Audio ≥ 1s  →  dual-model AND gate, both run in parallel:
          Smart Turn (prosody):  P ≥ 0.65  →  audio says "complete"
          LiveKit TD (semantics): P ≥ 0.003 →  text is not structurally mid-sentence
          Result: Smart Turn AND (NOT LiveKit-veto)

          LiveKit does NOT trigger responses on its own — it only blocks Smart
          Turn when the transcript ends mid-sentence (trailing "and", "because",
          "So the approach I would take is", etc.). Smart Turn remains the
          primary trigger; LiveKit just prevents prosodic false positives.

      Audio < 1s  →  syntactic heuristic only.
          Too little audio for Smart Turn to be meaningful.
    """
    loop = asyncio.get_running_loop()

    if len(audio) >= MIN_AUDIO_SAMPLES:
        st_session, extractor = _load_smart_turn()
        lk_session, tokenizer = _load_livekit_td()

        st_prob, lk_prob = await asyncio.gather(
            loop.run_in_executor(
                None, _predict_smart_turn_sync, st_session, extractor, audio
            ),
            loop.run_in_executor(
                None, _predict_livekit_sync,
                lk_session, tokenizer, transcript, last_assistant_turn
            ),
        )

        st_done  = st_prob >= ST_THRESHOLD
        lk_vetos = lk_prob < LK_VETO
        result   = st_done and not lk_vetos

        print(
            f"[turn_detection] ST={st_prob:.3f}({'✓' if st_done else '✗'}) "
            f"LK={lk_prob:.4f}({'VETO' if lk_vetos else 'ok'}) "
            f"-> {'RESPOND' if result else 'wait'} "
            f"| {len(audio)/SAMPLE_RATE:.1f}s | {transcript[:60]!r}"
        )
        return result

    else:
        result = not _is_mid_sentence(transcript)
        print(
            f"[turn_detection] audio too short ({len(audio)} samples), "
            f"heuristic -> {'RESPOND' if result else 'BLOCK'} "
            f"| {transcript[:60]!r}"
        )
        return result
