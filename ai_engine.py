"""
Joy Bot - Gemini Multi-Modal Voice Intelligence Engine
Handles real-time duplex voice conversations and text with context memory.
Equipped with fallback model pool, silence detection, and human persona tuning.
"""

import os
import re
import struct
import math
import logging
from typing import List, Dict, Optional, Tuple
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, PROMPTS

logger = logging.getLogger("JoyAI")

# Fallback pool prioritizing fast, responsive, and available models
MODEL_POOL = [
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash"
]

# Initialize Gemini Client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

def get_gemini_client() -> genai.Client:
    global client
    if client is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured in .env or environment!")
        client = genai.Client(api_key=key)
    return client

def is_wav_audio_silent(wav_bytes: bytes, threshold_rms: float = 220.0, threshold_peak: int = 550) -> bool:
    """
    Checks if a 16-bit mono PCM WAV has negligible energy (silence, room hiss, or breaths).
    Prevents calling the model on empty audio and eliminates silence hallucinations.
    """
    if len(wav_bytes) < 44:
        return True
    pcm_data = wav_bytes[44:]
    num_samples = len(pcm_data) // 2
    if num_samples < 3200:  # less than 0.2s at 16kHz
        return True

    samples = struct.unpack(f"<{num_samples}h", pcm_data[:num_samples*2])
    peak = max(abs(s) for s in samples)
    if peak < threshold_peak:
        return True

    sum_squares = sum(s * s for s in samples)
    rms = math.sqrt(sum_squares / num_samples)
    return rms < threshold_rms

def generate_text_reply(user_text: str, mode: str = "companion", history: List[Dict[str, str]] = None, user_memory: Optional[str] = None) -> str:
    """Generates a warm, human conversational response to text input with automatic model fallback."""
    ai_client = get_gemini_client()
    system_instruction = PROMPTS.get(mode, PROMPTS["companion"])
    if user_memory:
        system_instruction += f"\n\n[USER'S PAST MEMORIES IMPORTED FROM PREVIOUS AI COMPANION]:\n{user_memory}\nYou already know the user intimately from this background. Naturally reflect their interests, personality, and history."
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "Friend" if turn["role"] == "user" else "Joy"
            conversation_context += f"{role_label}: {turn['content']}\n"
    
    prompt = (
        f"{conversation_context}"
        f"Friend: {user_text}\n"
        f"Joy:"
    )
    
    last_err = None
    for model_name in MODEL_POOL:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.75,
                    max_output_tokens=100
                )
            )
            raw_reply = response.text.strip() if response.text else ""
            cleaned = re.sub(r'^[\s\*]*(?:REPLY|JOY|RESPONSE)[\s\*]*:\s*[\s\*]*', '', raw_reply, flags=re.IGNORECASE)
            return cleaned.strip() if cleaned else "Hey! I'm here. What's on your mind?"
        except Exception as e:
            last_err = e
            logger.warning(f"Model {model_name} failed for text: {e}. Trying next...")

    logger.error(f"All models failed for text reply: {last_err}")
    return "Hey! I'm here. What's on your mind?"

def parse_gemini_voice_output(raw_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Cleanly parses labeled Gemini output into (transcript, reply) with complete label stripping."""
    if not raw_text:
        return (None, None)

    # Detect explicit silence tokens
    if "[SILENCE]" in raw_text.upper() or "[NO_SPEECH]" in raw_text.upper():
        if "REPLY:" in raw_text:
            parts = raw_text.split("REPLY:", 1)
            rep = parts[1].strip()
            if "[SILENCE]" in rep.upper() or "[NONE]" in rep.upper() or not rep:
                return (None, None)
        else:
            return (None, None)

    # Extract labeled sections
    m_tr = re.search(r'(?:TRANSCRIPT|USER_SAID|USER)\s*:\s*(.*?)(?=(?:REPLY|JOY|RESPONSE)\s*:|$)', raw_text, re.DOTALL | re.IGNORECASE)
    transcript = m_tr.group(1).strip() if m_tr else ""

    m_rep = re.search(r'(?:REPLY|JOY|RESPONSE)\s*:\s*(.*)', raw_text, re.DOTALL | re.IGNORECASE)
    reply = m_rep.group(1).strip() if m_rep else ""

    if not reply and not transcript:
        reply = raw_text.strip()
        transcript = "Voice Note"
    elif not reply and transcript:
        reply = transcript
        transcript = "Voice Note"

    # Strip prefixes and extraneous markdown/quotes
    reply = re.sub(r'^[\s\*]*(?:REPLY|JOY|RESPONSE)[\s\*]*:\s*[\s\*]*', '', reply, flags=re.IGNORECASE)
    reply = re.sub(r'^[\"\'\*\s]+|[\"\'\*\s]+$', '', reply)

    transcript = re.sub(r'^[\s\*]*(?:TRANSCRIPT|USER_SAID|USER)[\s\*]*:\s*[\s\*]*', '', transcript, flags=re.IGNORECASE)
    transcript = re.sub(r'^[\"\'\*\s]+|[\"\'\*\s]+$', '', transcript)

    if "[SILENCE]" in transcript.upper() or not transcript:
        transcript = "Voice Note"

    return (transcript, reply)

def generate_voice_reply(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    mode: str = "companion",
    history: List[Dict[str, str]] = None,
    user_memory: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Directly processes audio bytes from the voice call using Gemini's native audio comprehension.
    Returns: (transcript, joy_reply) or (None, None) if audio is silent.
    """
    clean_mime = mime_type.split(";")[0].strip() if mime_type else "audio/wav"

    # Pre-flight energy audit: reject silence immediately before sending to Gemini
    if "wav" in clean_mime and is_wav_audio_silent(audio_bytes):
        logger.info("Discarded silent WAV chunk (< energy threshold). Skipping Gemini call.")
        return (None, None)

    ai_client = get_gemini_client()
    system_instruction = PROMPTS.get(mode, PROMPTS["companion"])
    if user_memory:
        system_instruction += f"\n\n[USER'S PAST MEMORIES IMPORTED FROM PREVIOUS AI COMPANION]:\n{user_memory}\n"
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "Friend" if turn["role"] == "user" else "Joy"
            conversation_context += f"{role_label}: {turn['content']}\n"

    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)
    
    instruction_prompt = (
        f"You are Joy on a direct live phone call with your friend.\n"
        f"Recent conversation so far:\n{conversation_context}\n\n"
        f"Listen carefully to the audio clip.\n"
        f"Instructions:\n"
        f"1. Transcribe what the user said in the audio. If the audio contains only silence, static, or breathing, write: [SILENCE]\n"
        f"2. Respond naturally to what they actually said as Joy:\n"
        f"   - Sound like a real, lively human friend on a phone call. Laugh, react with warmth or curiosity ('Haha really?', 'Oh wow', 'Aww').\n"
        f"   - Ultra-Low Latency Rule: Keep it super brief: 1 to 2 snappy conversational sentences (under 20 words) so it flows with instant speed.\n"
        f"   - Never repeat robotic lines like 'Hi how are you' over and over.\n"
        f"   - If the audio is [SILENCE], respond with: [SILENCE]\n\n"
        f"Strict Output Format:\n"
        f"TRANSCRIPT: <what the user said, or [SILENCE]>\n"
        f"REPLY: <your friendly conversational reply to speak, or [SILENCE]>"
    )

    last_err = None
    for model_name in MODEL_POOL:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=[audio_part, instruction_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.75,
                    max_output_tokens=100
                )
            )
            raw_text = response.text.strip() if response.text else ""
            transcript, reply = parse_gemini_voice_output(raw_text)
            
            # If silence detected by model, return (None, None)
            if not reply or reply == "[SILENCE]" or "[SILENCE]" in raw_text[:30]:
                logger.info(f"Model {model_name} reported silence. No speech output.")
                return (None, None)

            logger.info(f"Model {model_name} voice reply: '{reply[:50]}...'")
            return transcript, reply

        except Exception as e:
            last_err = e
            logger.warning(f"Model {model_name} failed for audio: {e}. Trying fallback...")

    logger.error(f"All models failed for audio reply: {last_err}")
    return ("Voice Note", "I'm listening, friend! Could you say that once more?")
