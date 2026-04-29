import os
import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

client = DeepgramClient(
    DEEPGRAM_API_KEY,
    DeepgramClientOptions(options={"keepalive": "true"})
)

# endpointing=300: 300ms of silence triggers speech_final.
# Smart Turn v3 filters false triggers, so we can afford a short endpointing value
# for faster response time. Previously 500ms when the heuristic needed more time.
def get_live_options() -> LiveOptions:
    return LiveOptions(
        model="nova-2",
        language="en-US",
        smart_format=True,
        filler_words=True,
        interim_results=True,
        endpointing=600,
        utterance_end_ms="2000",  # fallback if speech_final doesn't fire
    )


async def create_deepgram_connection(on_transcript, on_utterance_end):
    """
    Opens a live Deepgram streaming WebSocket connection.

    on_transcript(text: str)
        Called with each final transcript segment as the user talks.

    on_utterance_end(full_transcript: str)
        Called when Deepgram's VAD detects end of speech (speech_final=True),
        or after utterance_end_ms of silence as fallback.
        full_transcript is the accumulated text for this speech segment.
        Smart Turn v3 runs in the caller — this just delivers the signal.

    Returns the live connection object.
    """
    connection = client.listen.asynclive.v("1")

    transcript_buffer = []

    async def _on_transcript(self, result, **kwargs):
        if not result.is_final:
            return
        sentence = result.channel.alternatives[0].transcript
        if sentence.strip():
            transcript_buffer.append(sentence)
            await on_transcript(sentence)

        if result.speech_final and transcript_buffer:
            full = " ".join(transcript_buffer).strip()
            transcript_buffer.clear()
            try:
                await on_utterance_end(full)
            except Exception as e:
                print(f"[stt] on_utterance_end error (non-fatal): {type(e).__name__}: {e}")

    async def _on_utterance_end(self, utterance_end, **kwargs):
        # Fallback: fires after utterance_end_ms of silence if speech_final didn't
        if transcript_buffer:
            full = " ".join(transcript_buffer).strip()
            transcript_buffer.clear()
            try:
                await on_utterance_end(full)
            except Exception as e:
                print(f"[stt] _on_utterance_end fallback error (non-fatal): {type(e).__name__}: {e}")

    async def _on_error(self, error, **kwargs):
        print(f"[stt] Deepgram error: {error}")

    connection.on(LiveTranscriptionEvents.Transcript, _on_transcript)
    connection.on(LiveTranscriptionEvents.UtteranceEnd, _on_utterance_end)
    connection.on(LiveTranscriptionEvents.Error, _on_error)

    started = await connection.start(get_live_options())
    if not started:
        raise RuntimeError("[stt] Failed to start Deepgram connection")

    print("[stt] Deepgram connection open")
    return connection


async def close_connection(connection):
    await connection.finish()
    print("[stt] Deepgram connection closed")
