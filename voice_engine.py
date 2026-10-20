"""
Joy Bot - Edge-TTS Speech Synthesis Engine
Generates human-like, expressive neural speech for Indian English, Tamil, and Hindi.
Operates with pure in-RAM streaming, timeout guards, and secondary voice fallback.
"""

import re
import asyncio
import logging
import edge_tts
from config import VOICE_MAP
from database import record_api_call

logger = logging.getLogger("VoiceEngine")

# Minimal valid MPEG 1 Layer 3 MP3 silence frame (128 kbps, 44.1 kHz, ~0.15s)
EMERGENCY_SILENCE_MP3 = (b'\xff\xfb\x90\x00' + b'\x00' * 413) * 5

# Fallback voice map if primary voice is throttling or network lags
SECONDARY_VOICE_MAP = {
    "female": "en-IN-NeerjaNeural",
    "indian": "en-IN-NeerjaNeural",
    "hindi": "hi-IN-SwaraNeural",
    "male": "en-IN-PrabhatNeural"
}

def clean_text_for_speech(text: str) -> str:
    """Removes markdown symbols, emojis, stage directions, and labels so speech sounds completely natural."""
    # Remove speaker prefixes and labels
    cleaned = re.sub(r'^(?:TRANSCRIPT|REPLY|JOY|USER):\s*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'(?:TRANSCRIPT|REPLY|JOY|USER):\s*', '', cleaned, flags=re.IGNORECASE)
    # Remove parenthetical / bracketed stage directions like (laughs), [chuckles]
    cleaned = re.sub(r'\(.*?\)', '', cleaned)
    cleaned = re.sub(r'\[.*?\]', '', cleaned)
    # Remove asterisks and markdown bold/italic/code cues like *laughs* or **word**
    cleaned = re.sub(r'\*+[^*]+\*+', '', cleaned)
    cleaned = re.sub(r'[*_#`~]', '', cleaned)
    # Remove URL links
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    # Strip emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"
        "]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub(r'', cleaned)
    # Replace multiple spaces/newlines with single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

async def _stream_tts_audio(clean_text: str, voice_name: str, timeout: float = 6.0) -> bytes:
    """Streams neural TTS audio directly into RAM without disk I/O."""
    comm = edge_tts.Communicate(clean_text, voice_name, pitch="+0Hz", rate="+0%")
    audio_chunks = []
    
    async def _fetch():
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)

    return await asyncio.wait_for(_fetch(), timeout=timeout)

async def synthesize_speech(text: str, voice_key: str = "female") -> bytes:
    """
    Synthesizes speech using Microsoft Edge Neural TTS with 100% in-RAM streaming,
    strict timeout guards, automatic secondary voice fallback, and emergency silence recovery.
    Returns: MP3 audio bytes (guaranteed valid).
    """
    try:
        record_api_call("tts", 1)
    except Exception:
        pass

    clean_text = clean_text_for_speech(text)
    if not clean_text:
        clean_text = "I'm listening!"
        
    primary_voice = VOICE_MAP.get(voice_key, VOICE_MAP.get("female", "en-IN-NeerjaNeural"))
    secondary_voice = SECONDARY_VOICE_MAP.get(voice_key, "en-US-JennyNeural")

    # Attempt 1: Stream directly in RAM with primary voice
    try:
        audio = await _stream_tts_audio(clean_text, primary_voice, timeout=6.0)
        if audio and len(audio) > 100:
            return audio
    except Exception as err1:
        logger.warning(f"Primary voice '{primary_voice}' streaming failed or timed out: {err1}. Trying fallback '{secondary_voice}'...")

    # Attempt 2: Stream directly in RAM with secondary fallback voice
    try:
        audio = await _stream_tts_audio(clean_text, secondary_voice, timeout=5.0)
        if audio and len(audio) > 100:
            return audio
    except Exception as err2:
        logger.error(f"Secondary voice '{secondary_voice}' also failed: {err2}. Returning emergency silence frame.")

    # Attempt 3: Return valid minimal MP3 silence frame so client audio pipeline never crashes
    return EMERGENCY_SILENCE_MP3
