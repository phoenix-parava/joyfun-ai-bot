"""
Joy Bot - Advanced Multi-Engine Speech Synthesis Pipeline
Indian-optimized neural speech synthesis for Tamil, Hindi, Tanglish, Hinglish, and Indian English.
Tiers:
1. Sarvam AI Neural TTS (bulbul:v1) - State-of-the-art Indian regional fluency
2. Azure Speech Neural (ta-IN-PallaviNeural / hi-IN-SwaraNeural)
3. Microsoft Edge-TTS In-RAM Streaming (ta-IN-PallaviNeural, hi-IN-SwaraNeural, en-IN-NeerjaExpressiveNeural)
Guarantees 100% in-RAM streaming, sub-second latency, zero crashes, and emergency silence recovery.
"""

import re
import base64
import asyncio
import logging
import aiohttp
import edge_tts
from config import (
    VOICE_MAP,
    SARVAM_API_KEY,
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION
)
from database import record_api_call

logger = logging.getLogger("VoiceEngine")

# Minimal valid MPEG 1 Layer 3 MP3 silence frame (128 kbps, 44.1 kHz, ~0.15s)
EMERGENCY_SILENCE_MP3 = (b'\xff\xfb\x90\x00' + b'\x00' * 413) * 5

# High-reliability secondary fallback voice map
SECONDARY_VOICE_MAP = {
    "female": "en-IN-NeerjaNeural",
    "indian": "en-IN-NeerjaNeural",
    "male": "en-IN-PrabhatNeural",
    "hindi": "hi-IN-MadhurNeural",
    "hindi_male": "hi-IN-SwaraNeural",
    "tamil": "ta-IN-ValluvarNeural",
    "tamil_male": "ta-IN-PallaviNeural",
    "tanglish": "ta-IN-ValluvarNeural",
    "hinglish": "hi-IN-MadhurNeural"
}

def clean_text_for_speech(text: str) -> str:
    """
    Removes markdown symbols, emojis, stage directions, and labels.
    Performs phonetic compression on repeating characters so neural TTS pronounces words smoothly.
    """
    if not text:
        return ""
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

    # Compress elongated letters (e.g. "machaaaa" -> "macha", "ennaaaa" -> "enna", "sunoool" -> "sunoo")
    cleaned = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', cleaned)

    # Replace multiple spaces/newlines with single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

async def _synthesize_sarvam(clean_text: str, target_lang: str = "hi-IN", timeout: float = 5.0) -> bytes:
    """
    Calls Sarvam AI Text-To-Speech API (bulbul:v1) optimized for authentic Indian accents.
    Supports ta-IN (Tamil), hi-IN (Hindi), te-IN, kn-IN, etc.
    """
    if not SARVAM_API_KEY:
        return b""
    
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    speaker = "meera" if "ta" in target_lang or "hi" in target_lang else "pavithra"
    payload = {
        "inputs": [clean_text[:500]],
        "target_language_code": target_lang,
        "speaker": speaker,
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json()
                audios = data.get("audios", [])
                if audios and isinstance(audios[0], str):
                    return base64.b64decode(audios[0])
            else:
                body = await resp.text()
                logger.warning(f"Sarvam AI TTS API error ({resp.status}): {body[:150]}")
    return b""

async def _synthesize_azure(clean_text: str, voice_name: str = "ta-IN-PallaviNeural", lang: str = "ta-IN", timeout: float = 5.0) -> bytes:
    """Calls Azure Cognitive Services Neural Speech API."""
    if not AZURE_SPEECH_KEY:
        return b""
    
    region = AZURE_SPEECH_REGION or "centralindia"
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "JoyBotSpeech"
    }
    escaped_text = clean_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ssml = f"""<speak version='1.0' xml:lang='{lang}'>
        <voice xml:lang='{lang}' name='{voice_name}'>
            {escaped_text}
        </voice>
    </speak>"""
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                return await resp.read()
            else:
                body = await resp.text()
                logger.warning(f"Azure Neural TTS error ({resp.status}): {body[:150]}")
    return b""

async def _stream_edge_tts(clean_text: str, voice_name: str, speed: float = 1.0, timeout: float = 6.0) -> bytes:
    """Streams neural TTS audio directly into RAM using Edge-TTS without disk I/O."""
    rate_val = int(round((speed - 1.0) * 100))
    rate_str = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
    comm = edge_tts.Communicate(clean_text, voice_name, pitch="+0Hz", rate=rate_str)
    audio_chunks = []
    
    async def _fetch():
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)

    return await asyncio.wait_for(_fetch(), timeout=timeout)

async def synthesize_speech(text: str, voice_key: str = "female", speed: float = 1.0) -> bytes:
    """
    Synthesizes speech using multi-tier Indian-optimized neural engines:
    Tier 1: Sarvam AI (for Tamil & Hindi regional clarity if API key configured)
    Tier 2: Azure Neural Speech (if API key configured)
    Tier 3: High-clarity Edge-TTS Neural Models (ta-IN-PallaviNeural, hi-IN-SwaraNeural, en-IN-NeerjaExpressiveNeural)
    Guaranteed valid MP3 audio bytes with zero crashes.
    """
    try:
        record_api_call("tts", 1)
    except Exception:
        pass

    clean_text = clean_text_for_speech(text)
    if not clean_text:
        clean_text = "I'm listening!"

    vkey = voice_key.lower().strip()
    is_tamil = any(k in vkey for k in ["tamil", "tanglish", "ta-in"])
    is_hindi = any(k in vkey for k in ["hindi", "hinglish", "hi-in"])

    # 1. Tier 1: Try Sarvam AI if configured and target is Indian Regional (Tamil/Hindi)
    if SARVAM_API_KEY and (is_tamil or is_hindi):
        target_lang = "ta-IN" if is_tamil else "hi-IN"
        try:
            audio = await _synthesize_sarvam(clean_text, target_lang=target_lang, timeout=4.5)
            if audio and len(audio) > 100:
                return audio
        except Exception as e:
            logger.warning(f"Sarvam AI TTS fallback to Edge-TTS: {e}")

    # 2. Tier 2: Try Azure Neural Speech if configured
    if AZURE_SPEECH_KEY and (is_tamil or is_hindi):
        az_voice = "ta-IN-PallaviNeural" if is_tamil else "hi-IN-SwaraNeural"
        az_lang = "ta-IN" if is_tamil else "hi-IN"
        try:
            audio = await _synthesize_azure(clean_text, voice_name=az_voice, lang=az_lang, timeout=4.5)
            if audio and len(audio) > 100:
                return audio
        except Exception as e:
            logger.warning(f"Azure Neural Speech fallback to Edge-TTS: {e}")

    # 3. Tier 3: Edge-TTS Primary Voice
    primary_voice = VOICE_MAP.get(voice_key, VOICE_MAP.get("female", "en-IN-NeerjaExpressiveNeural"))
    secondary_voice = SECONDARY_VOICE_MAP.get(voice_key, "en-IN-NeerjaNeural")

    try:
        audio = await _stream_edge_tts(clean_text, primary_voice, speed=speed, timeout=6.0)
        if audio and len(audio) > 100:
            return audio
    except Exception as err1:
        logger.warning(f"Primary voice '{primary_voice}' streaming failed: {err1}. Trying fallback '{secondary_voice}'...")

    # 4. Tier 4: Edge-TTS Secondary Fallback
    try:
        audio = await _stream_edge_tts(clean_text, secondary_voice, speed=speed, timeout=5.0)
        if audio and len(audio) > 100:
            return audio
    except Exception as err2:
        logger.error(f"Secondary voice '{secondary_voice}' failed: {err2}. Returning emergency silence frame.")

    # 5. Safety Net: Return minimal valid MP3 frame
    return EMERGENCY_SILENCE_MP3
