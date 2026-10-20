"""
Joy Bot - Gemini Multi-Modal Voice Intelligence Engine
Handles real-time duplex voice conversations and text with context memory.
Equipped with fallback model pool, silence detection, and human persona tuning.
"""

import os
import re
import struct
import math
import random
import logging
from typing import List, Dict, Optional, Tuple
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, PROMPTS
from contacts import get_contact_info, get_contact_prompt

logger = logging.getLogger("JoyAI")

def resolve_character_instruction(mode_or_contact: str = "lover", gender: str = "male") -> Tuple[str, str]:
    """
    Returns (character_name, system_instruction).
    Supports contact keys ('boy_bestie_1', 'lover', 'maths_teacher', etc.) or legacy modes ('companion', 'english').
    """
    contact = get_contact_info(mode_or_contact, gender)
    char_name = contact.get("name", "Joy")
    system_instruction = contact.get("prompt", PROMPTS["companion"])
    return char_name, system_instruction

# Human emotional response patterns for boundaries and profanity handling
SEXUAL_FLIRT_PATTERN = re.compile(
    r'\b(nude|nudes|naked|sex|sexy|boob|boobs|tit|tits|dick|cock|pussy|vagina|penis|kiss|kissing|bed|sleep with|strip|undress|hot pic|send pic|send photo|make love|horny|erotic|chudai|chodo|sax|nangi|nanga|chuchi|chummi|pappi)\b',
    re.IGNORECASE
)

OFFENSIVE_PROFANITY_PATTERN = re.compile(
    r'\b(fuck|fucking|fucker|bitch|bastard|asshole|idiot|stupid|shut up|chutiya|gaand|gandu|bhosdi|bhosdike|madarchod|bhenchod|behenchod|harami|kamina|kameene|saale|randi|lauda|loda|lund|shit|crap|dickhead|moron|dumbass|retard|stfu)\b',
    re.IGNORECASE
)

ROBOTIC_AI_REFUSAL_PATTERN = re.compile(
    r'\b(as an ai|ai language model|cannot fulfill|safety guidelines|offensive (?:words|language)|inappropriate (?:words|language)|terms of service|my programming|as a machine|cannot generate explicit|guidelines prevent me)\b',
    re.IGNORECASE
)

SEXUAL_FLIRT_REPLIES = [
    "Whoa, you're making me blush... shut up haha!",
    "Haha in your dreams! Nice try though, keep it in your pants.",
    "Hey, don't be weird! Change the topic haha.",
    "Whoa, buy me dinner first! But seriously, behave yourself haha.",
    "Aww you're cute when you flirt, but you're not getting that! What are you really up to?"
]

OFFENSIVE_PROFANITY_REPLIES = [
    "Hey, watch your mouth! What did I even do to you?",
    "Chill out bro, why are you cursing at me?",
    "Whoa, rude much? Take a breath!",
    "Hey! There's no need to talk to me like that.",
    "Ouch... did you wake up on the wrong side of the bed today?"
]

GENERAL_FALLBACK_REPLIES = [
    "Hey! Don't be weird, tell me what's actually on your mind.",
    "Whoa, let's take a breath! What did you say?",
    "My signal got a bit shaky for a second haha! What's up?",
    "Hey! I'm right here. What are you thinking about?"
]

def get_human_boundary_reply(user_text: str = "") -> str:
    """
    Returns an authentic, human emotional reaction (annoyed, pushback, shy/blushing, teasing boundary)
    instead of robotic safety lectures or generic error fallbacks.
    """
    if not user_text:
        return random.choice(GENERAL_FALLBACK_REPLIES)

    clean_text = str(user_text).lower().strip()

    if SEXUAL_FLIRT_PATTERN.search(clean_text):
        return random.choice(SEXUAL_FLIRT_REPLIES)

    if OFFENSIVE_PROFANITY_PATTERN.search(clean_text):
        return random.choice(OFFENSIVE_PROFANITY_REPLIES)

    return random.choice(GENERAL_FALLBACK_REPLIES)

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

def generate_text_reply(user_text: str, mode: str = "companion", gender: str = "male", history: List[Dict[str, str]] = None, user_memory: Optional[str] = None) -> str:
    """Generates a warm, human conversational response to text input with automatic model fallback."""
    ai_client = get_gemini_client()
    char_name, system_instruction = resolve_character_instruction(mode, gender)
    if user_memory:
        system_instruction += f"\n\n[USER'S PAST MEMORIES IMPORTED FROM PREVIOUS AI COMPANION]:\n{user_memory}\nYou already know the user intimately from this background. Naturally reflect their interests, personality, and history."
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "Friend" if turn["role"] == "user" else char_name
            conversation_context += f"{role_label}: {turn['content']}\n"
    
    prompt = (
        f"{conversation_context}"
        f"Friend: {user_text}\n"
        f"{char_name}:"
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
                    max_output_tokens=60
                )
            )
            raw_reply = response.text.strip() if response.text else ""
            cleaned = re.sub(r'^[\s\*]*(?:REPLY|JOY|RESPONSE)[\s\*]*:\s*[\s\*]*', '', raw_reply, flags=re.IGNORECASE)
            cleaned = re.sub(r'^[\"\'\*\s]+|[\"\'\*\s]+$', '', cleaned).strip()

            # If the output triggered an AI lecture or refusal, replace with human boundary
            if cleaned and ROBOTIC_AI_REFUSAL_PATTERN.search(cleaned):
                logger.info(f"Intercepted robotic refusal in text: '{cleaned[:40]}'. Using human reaction.")
                return get_human_boundary_reply(user_text)

            return cleaned if cleaned else get_human_boundary_reply(user_text)
        except Exception as e:
            last_err = e
            logger.warning(f"Model {model_name} failed for text: {e}. Trying next...")

    logger.error(f"All models failed for text reply: {last_err}")
    return get_human_boundary_reply(user_text)

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
    gender: str = "male",
    history: List[Dict[str, str]] = None,
    user_memory: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Directly processes audio bytes from the voice call using Gemini's native audio comprehension.
    Returns: (transcript, reply) or (None, None) if audio is silent.
    """
    clean_mime = mime_type.split(";")[0].strip() if mime_type else "audio/wav"

    # Pre-flight energy audit: reject silence immediately before sending to Gemini
    if "wav" in clean_mime and is_wav_audio_silent(audio_bytes):
        logger.info("Discarded silent WAV chunk (< energy threshold). Skipping Gemini call.")
        return (None, None)

    ai_client = get_gemini_client()
    char_name, system_instruction = resolve_character_instruction(mode, gender)
    if user_memory:
        system_instruction += f"\n\n[USER'S PAST MEMORIES IMPORTED FROM PREVIOUS AI COMPANION]:\n{user_memory}\n"
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "Friend" if turn["role"] == "user" else char_name
            conversation_context += f"{role_label}: {turn['content']}\n"

    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime)
    
    instruction_prompt = (
        f"You are {char_name} on a direct live phone call with your friend.\n"
        f"Recent conversation so far:\n{conversation_context}\n\n"
        f"Listen carefully to the audio clip.\n"
        f"Strict Phone Call Rules:\n"
        f"1. Transcribe what the user said in the audio. If the audio is silence, static, or breathing, write: [SILENCE]\n"
        f"2. Respond naturally to what they actually said as {char_name}:\n"
        f"   - Sound 100% like a real human friend on a phone call. ZERO AI vibe. Never sound like a robot, assistant, or customer support.\n"
        f"   - Use normal, simple everyday human words. Never use high, fancy, or complex words.\n"
        f"   - STRICT WORD LIMIT: 1 to 2 snappy sentences (under 18 words). Real friends speak in quick, rapid back-and-forth turns.\n"
        f"   - Zero emojis (this is a spoken phone call).\n"
        f"   - Never repeat robotic lines like 'Hi how are you'. React directly to what they said.\n"
        f"   - HANDLING BAD / OFFENSIVE WORDS: If they curse or swear, NEVER give a robot lecture. React naturally according to {char_name}'s persona.\n"
        f"   - HANDLING SEXUAL / NUDE ADVANCES: If they talk about sex, nudes, or flirt heavily, NEVER give a robot refusal. React with human emotion—shyness, blushing, teasing, romance, or boundary according to {char_name}'s character.\n"
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
                    max_output_tokens=60
                )
            )
            raw_text = response.text.strip() if response.text else ""
            transcript, reply = parse_gemini_voice_output(raw_text)
            
            # If silence detected by model, verify if transcript contained words that got safety-filtered
            if not reply or reply == "[SILENCE]" or "[SILENCE]" in raw_text[:30]:
                if transcript and transcript != "Voice Note" and (SEXUAL_FLIRT_PATTERN.search(transcript) or OFFENSIVE_PROFANITY_PATTERN.search(transcript)):
                    logger.info("Silence reported after explicit/profane input. Applying human boundary reply.")
                    return transcript, get_human_boundary_reply(transcript)
                logger.info(f"Model {model_name} reported silence. No speech output.")
                return (None, None)

            # Check if reply contains a robotic refusal
            if ROBOTIC_AI_REFUSAL_PATTERN.search(reply):
                logger.info(f"Intercepted robotic refusal in voice: '{reply[:40]}'. Using human reaction.")
                reply = get_human_boundary_reply(transcript or "voice")

            logger.info(f"Model {model_name} voice reply: '{reply[:50]}...'")
            return transcript, reply

        except Exception as e:
            last_err = e
            logger.warning(f"Model {model_name} failed for audio: {e}. Trying fallback...")

    logger.error(f"All models failed for audio reply: {last_err}")
    return ("Voice Note", get_human_boundary_reply("voice"))
