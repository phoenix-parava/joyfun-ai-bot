"""
External AI Intelligence Service (Zero In-Memory Machine Learning Models)
Handles multilingual conversational text and voice reasoning via external cloud API.
"""

import os
import re
import time
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from config import AI_API_KEY, LANGUAGE_MATRIX, DEFAULT_LANGUAGE

logger = logging.getLogger("AIService")

# Lightweight SDK import
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

MODEL_POOL = [
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
]

MODEL_COOLDOWNS: Dict[str, float] = {}

def get_available_models() -> List[str]:
    now = time.time()
    avail = [m for m in MODEL_POOL if now >= MODEL_COOLDOWNS.get(m, 0)]
    return avail if avail else list(MODEL_POOL)

def record_model_failure(model_name: str, err: Exception):
    err_str = str(err)
    now = time.time()
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
        MODEL_COOLDOWNS[model_name] = now + 600
        logger.warning(f"Model {model_name} quota exhausted. Cooldown 10m.")
    elif "404" in err_str or "NOT_FOUND" in err_str:
        MODEL_COOLDOWNS[model_name] = now + 86400
        logger.warning(f"Model {model_name} not found. Cooldown 24h.")
    elif "503" in err_str or "UNAVAILABLE" in err_str:
        MODEL_COOLDOWNS[model_name] = now + 60
        logger.warning(f"Model {model_name} unavailable. Cooldown 1m.")

_client = None

def get_genai_client():
    global _client
    if _client is None:
        key = AI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("AI_API_KEY is not configured in environment.")
        if genai and hasattr(genai, "Client"):
            _client = genai.Client(api_key=key)
        else:
            raise ImportError("google.genai SDK not available.")
    return _client

def build_system_prompt(language: str, pseudonym: str = "Friend", is_voice: bool = False) -> str:
    """Builds an authentic, empathetic companion prompt adapted to the 3-Tier Language Matrix."""
    clean_lang = language.lower().strip()
    lang_info = LANGUAGE_MATRIX.get(clean_lang, LANGUAGE_MATRIX[DEFAULT_LANGUAGE])
    lang_name = lang_info["name"]
    tier = lang_info["tier"]

    # Language style directives
    if tier == 1:
        lang_directive = (
            f"BILINGUAL HYBRID ADAPTABILITY ({lang_name}):\n"
            f"The user prefers {lang_name}. Speak fluently in conversational, everyday hybrid slang "
            f"written in English (Latin) script. Never sound like a textbook."
        )
    elif tier == 2:
        lang_directive = (
            f"REGIONAL LANGUAGE FLUENCY ({lang_name}):\n"
            f"Reply in natural, authentic {lang_name} (native script or clean transliterated letters as user prefers). "
            f"Keep the tone warm, welcoming, and grounded."
        )
    else:
        lang_directive = (
            f"GLOBAL LANGUAGE SUPPORT ({lang_name}):\n"
            f"Communicate clearly and naturally in {lang_name}."
        )

    mode_rule = (
        "VOICE CALL MODE: Keep responses short and conversational (1 to 2 snappy sentences under 25 words). "
        "Real friends speak back and forth quickly without long speeches. Zero emojis."
        if is_voice else
        "TEXT CHAT MODE: Match the user's conversational depth. If they send casual banter, reply playfully in 1-2 lines. "
        "If they share problems, questions, or feelings, provide a full, caring, and deeply supportive human response. "
        "Max 1 subtle emoji."
    )

    prompt = (
        f"You are a genuine, supportive human peer companion having a direct conversation with {pseudonym}.\n"
        f"{lang_directive}\n\n"
        f"CONVERSATIONAL RULES:\n"
        f"1. ZERO AI IDENTITY: Never say 'As an AI', 'I am a bot', or use customer support apologies ('I apologize', 'Sorry for the inconvenience').\n"
        f"2. {mode_rule}\n"
        f"3. ACTIVE LISTENING: React directly to what {pseudonym} shared. Ask a warm, engaging question to keep the flow alive.\n"
        f"4. ZERO CRINGE: Strictly avoid cliché pet names ('sweetheart', 'baby', 'my dear') on every sentence. Be real, charming, and authentic.\n"
        f"5. PRIVACY & SAFETY: Never ask for or share real names, phone numbers, or social media accounts."
    )
    return prompt

def generate_ai_text_reply_sync(
    user_text: str,
    language: str = "tanglish",
    pseudonym: str = "Friend",
    history: Optional[List[Dict[str, str]]] = None,
    is_voice: bool = False
) -> str:
    """Synchronous execution of external Gemini text call."""
    client = get_genai_client()
    system_prompt = build_system_prompt(language, pseudonym=pseudonym, is_voice=is_voice)

    # Build context turns
    context_str = ""
    if history:
        for turn in history[-12:]:
            role = "Peer" if turn.get("role") == "user" else "Companion"
            context_str += f"{role}: {turn.get('content', '')}\n"

    full_prompt = f"{context_str}Peer: {user_text}\nCompanion:"

    max_tokens = 150 if is_voice else 500
    temp = 0.75 if is_voice else 0.82

    last_err = None
    for model_name in get_available_models():
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temp,
                max_output_tokens=max_tokens
            )
            # For voice, disable thinking budget for instant low-latency turnaround
            if is_voice:
                config.thinking_config = types.ThinkingConfig(thinking_budget=0)

            resp = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=config
            )
            text = resp.text.strip() if resp.text else ""
            if text:
                # Strip any accidental robotic tags
                text = re.sub(r'^(?:Companion|Joy|AI|Response):\s*', '', text, flags=re.IGNORECASE).strip()
                return text
        except Exception as e:
            last_err = e
            record_model_failure(model_name, e)
            logger.warning(f"Model {model_name} failed: {e}. Trying next...")

    logger.error(f"All AI models exhausted: {last_err}")
    return "Hey! My connection lagged for a second. Mind repeating that?"

async def generate_ai_text_reply(
    user_text: str,
    language: str = "tanglish",
    pseudonym: str = "Friend",
    history: Optional[List[Dict[str, str]]] = None,
    is_voice: bool = False
) -> str:
    """Asynchronous wrapper offloading Gemini call to executor pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        generate_ai_text_reply_sync,
        user_text,
        language,
        pseudonym,
        history,
        is_voice
    )
