"""
Joy Bot - Edge-TTS Speech Synthesis Engine
Generates human-like, expressive neural speech for Indian English and Hindi.
"""

import re
import asyncio
import tempfile
from pathlib import Path
import edge_tts
from config import VOICE_MAP

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

async def synthesize_speech(text: str, voice_key: str = "female") -> bytes:
    """
    Synthesizes speech using Microsoft Edge Neural TTS.
    Returns: MP3 audio bytes.
    """
    clean_text = clean_text_for_speech(text)
    if not clean_text:
        clean_text = "I'm listening!"
        
    voice_name = VOICE_MAP.get(voice_key, VOICE_MAP["female"])
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
    try:
        communicate = edge_tts.Communicate(clean_text, voice_name, pitch="+0Hz", rate="+0%")
        await communicate.save(tmp_path)
        
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
            
        return audio_bytes
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
