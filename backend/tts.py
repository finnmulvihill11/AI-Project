import os
from elevenlabs.client import AsyncElevenLabs

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# ---------------------------------------------------------------------------
# Voice selection
# Replace this ID with your chosen voice from elevenlabs.io/voice-library.
# Pick something neutral and professional — sounds like a real interviewer.
# To get the ID: open a voice in the library → "Use" → copy the Voice ID string.
# ---------------------------------------------------------------------------
INTERVIEWER_VOICE_ID = "wqKtomEaI22L2mdOxll3"

client = AsyncElevenLabs(api_key=ELEVENLABS_API_KEY)


async def synthesize_speech(text: str, voice_id: str = INTERVIEWER_VOICE_ID):
    """
    Stream TTS audio from ElevenLabs Turbo v2.
    Yields audio chunks (bytes) as they arrive — the interview loop sends each
    chunk to the frontend via WebSocket immediately, so the user hears the AI
    start speaking before the full audio is generated.

    Usage in interview loop:
        async for chunk in synthesize_speech(response_text):
            await websocket.send_bytes(chunk)
    """
    async for chunk in client.text_to_speech.stream(
        text=text,
        voice_id=voice_id,
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    ):
        if chunk:
            yield chunk


async def synthesize_speech_full(text: str, voice_id: str = INTERVIEWER_VOICE_ID) -> bytes:
    """
    Blocking TTS — collects all chunks and returns complete audio as bytes.
    Used for pre-generating the AI's opening line during the waiting room so
    it plays instantly when the interview starts (zero TTS latency on first utterance).

    Usage:
        opening_audio = await synthesize_speech_full(opening_line)
        # store to session, play immediately when interview begins
    """
    audio_chunks = []
    async for chunk in synthesize_speech(text, voice_id):
        audio_chunks.append(chunk)
    return b"".join(audio_chunks)
