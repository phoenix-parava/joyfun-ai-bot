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
    """Removes markdown symbols, emojis, and code formatting so speech sounds natural."""
    # Remove markdown bold/italics
    cleaned = re.sub(r'[*_#`~]', '', text)
    # Remove URL links
    cleaned = re.sub(r'https?://\S+', '', cleaned)
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
        communicate = edge_tts.Communicate(clean_text, voice_name, pitch="+4Hz", rate="+4%")
        await communicate.save(tmp_path)

        
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
            
        return audio_bytes
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
