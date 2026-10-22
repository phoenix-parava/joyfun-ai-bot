"""
Unified FastAPI Server & Aiogram 3 Telegram Bot Architecture
Single process, single worker (--workers 1), strict 500-600 MB RAM budget on Render.
"""

import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import (
    BOT_TOKEN,
    PORT,
    WEBHOOK_URL,
    MINI_APP_URL,
    CREATOR_TELEGRAM_HANDLE,
    RTC_ICE_SERVERS,
    LANGUAGE_MATRIX,
    BASE_DIR
)
from database import (
    init_db,
    get_or_create_user,
    get_user,
    accept_terms,
    complete_onboarding,
    update_user_settings,
    get_user_quota_summary,
    save_feedback
)
from security import (
    validate_telegram_init_data,
    validate_and_clean_pseudonym,
    sanitize_pii
)
from bot_handlers import setup_bot_commands, register_handlers
from signaling import signaling_hub

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("UnifiedServer")

# Initialize Aiogram Bot & Dispatcher
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None

if BOT_TOKEN:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp, bot)

polling_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing system database...")
    await init_db()

    if bot and dp:
        await setup_bot_commands(bot)
        # Determine Webhook vs Polling
        if WEBHOOK_URL:
            webhook_path = f"{WEBHOOK_URL}/webhook/telegram"
            logger.info(f"Setting Telegram Webhook to: {webhook_path}")
            await bot.set_webhook(
                url=webhook_path,
                drop_pending_updates=False,
                allowed_updates=["message", "callback_query"]
            )
        else:
            logger.info("WEBHOOK_URL not set. Launching internal async polling worker...")
            global polling_task
            polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))

    yield

    # Shutdown sequence
    logger.info("Shutting down application...")
    if polling_task and not polling_task.done():
        polling_task.cancel()
    if bot:
        await bot.session.close()

app = FastAPI(title="Secure P2P WebRTC Communication Platform", lifespan=lifespan)

# Mount static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- Telegram Webhook Endpoint ---
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Processes incoming Telegram updates via Webhook."""
    if not bot or not dp:
        return JSONResponse({"status": "bot_not_configured"}, status_code=503)

    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot=bot, update=update)
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error(f"Error handling Telegram webhook update: {e}")
        return JSONResponse({"ok": False, "error": "Internal processing error"}, status_code=500)

# --- Root HTML (Telegram Mini App) ---
@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    """Serves the formal Telegram Mini App UI."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h3>Communication App loading...</h3>")

@app.get("/health")
async def health_check():
    """Lightweight health check for Render container lifecycle."""
    return {
        "status": "online",
        "service": "P2P WebRTC & AI Communication Hub",
        "workers": 1,
        "memory_safe": True
    }

# --- Pydantic Request Schemas ---
class AuthRequest(BaseModel):
    init_data: str

class AcceptTermsRequest(BaseModel):
    init_data: str

class OnboardingRequest(BaseModel):
    init_data: str
    pseudonym: str
    language: str
    modality: str = "voice"
    partner_preference: str = "real_or_ai"

class SettingsRequest(BaseModel):
    init_data: str
    pseudonym: Optional[str] = None
    language: Optional[str] = None
    modality: Optional[str] = None
    partner_preference: Optional[str] = None
    low_data_mode: Optional[bool] = None
    speech_rate: Optional[float] = None
    email_address: Optional[str] = None
    email_enabled: Optional[bool] = None

class FeedbackRequest(BaseModel):
    init_data: str
    message: str

# Helper Dependency: Authenticates initData
def authenticate_user(init_data: str) -> dict:
    user_info = validate_telegram_init_data(init_data)
    if not user_info or "id" not in user_info:
        # Fallback check for user_id key
        uid = user_info.get("id") or user_info.get("user_id") if user_info else None
        if not uid:
            raise HTTPException(status_code=401, detail="Cryptographic verification failed")
    return user_info

# --- REST API Endpoints ---
@app.get("/api/config")
async def get_public_config():
    """Provides public WebRTC STUN/TURN configurations and language matrix."""
    return {
        "ice_servers": RTC_ICE_SERVERS,
        "language_matrix": LANGUAGE_MATRIX,
        "creator_handle": CREATOR_TELEGRAM_HANDLE
    }

@app.post("/api/auth")
async def api_auth(req: AuthRequest):
    """Authenticates Telegram Mini App session via cryptographic HMAC-SHA256 signature."""
    user_info = authenticate_user(req.init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))
    default_name = user_info.get("first_name", "") or user_info.get("username", "")

    user = await get_or_create_user(user_id, default_name=default_name)
    quotas = await get_user_quota_summary(user_id)

    return {
        "ok": True,
        "user": user,
        "quotas": quotas
    }

@app.post("/api/user/terms/accept")
async def api_accept_terms(req: AcceptTermsRequest):
    """Enforces Mandatory Accept-Only Privacy Gate."""
    user_info = authenticate_user(req.init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))

    await accept_terms(user_id)
    user = await get_user(user_id)
    return {"ok": True, "user": user}

@app.post("/api/user/onboarding")
async def api_complete_onboarding(req: OnboardingRequest):
    """Saves Pre-Chat Onboarding choices."""
    user_info = authenticate_user(req.init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))

    valid_name, clean_name = validate_and_clean_pseudonym(req.pseudonym)
    if not valid_name:
        raise HTTPException(status_code=400, detail="Invalid display name (must be 3-20 characters without contact info).")

    await complete_onboarding(
        user_id,
        clean_name,
        req.language,
        req.modality,
        req.partner_preference
    )
    user = await get_user(user_id)
    return {"ok": True, "user": user}

@app.post("/api/user/settings")
async def api_update_settings(req: SettingsRequest):
    """Updates user preferences inside Settings tab."""
    user_info = authenticate_user(req.init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))

    kwargs = {}
    if req.pseudonym is not None:
        valid_name, clean_name = validate_and_clean_pseudonym(req.pseudonym)
        if not valid_name:
            raise HTTPException(status_code=400, detail="Invalid display name (must be 3-20 characters without contact info).")
        kwargs["pseudonym"] = clean_name

    if req.language is not None:
        kwargs["language"] = req.language
    if req.modality is not None:
        kwargs["modality"] = req.modality
    if req.partner_preference is not None:
        kwargs["partner_preference"] = req.partner_preference
    if req.low_data_mode is not None:
        kwargs["low_data_mode"] = 1 if req.low_data_mode else 0
    if req.speech_rate is not None:
        kwargs["speech_rate"] = max(0.5, min(2.0, float(req.speech_rate)))
    if req.email_address is not None:
        kwargs["email_address"] = req.email_address.strip()
    if req.email_enabled is not None:
        kwargs["email_enabled"] = 1 if req.email_enabled else 0

    user = await update_user_settings(user_id, **kwargs)
    return {"ok": True, "user": user}

@app.get("/api/user/quota")
async def api_get_quota(init_data: str):
    """Returns server-authoritative live countdown balances."""
    user_info = authenticate_user(init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))
    quotas = await get_user_quota_summary(user_id)
    return {"ok": True, "quotas": quotas}

@app.post("/api/feedback")
async def api_submit_feedback(req: FeedbackRequest):
    """Collects user feedback from Mini App and routes formatted card to Admin."""
    user_info = authenticate_user(req.init_data)
    user_id = int(user_info.get("id") or user_info.get("user_id"))
    user = await get_user(user_id) or {}

    pseudonym = user.get("pseudonym", "Anonymous")
    email = user.get("email_address") if user.get("email_enabled") else "Not Enabled"
    lang = user.get("language", "tanglish")

    fb_id = await save_feedback(user_id, pseudonym, email or "Not Enabled", lang, req.message)

    # Route alert to Admin
    from config import ADMIN_CHAT_ID
    if bot and ADMIN_CHAT_ID:
        admin_card = (
            f"📬 **New User Feedback #{fb_id} (via Mini App)**\n\n"
            f"• **Pseudonym:** `{pseudonym}`\n"
            f"• **Telegram ID:** `{user_id}`\n"
            f"• **Cloud Email:** `{email or 'Not Enabled'}`\n"
            f"• **Language:** `{lang}`\n\n"
            f"**Message:**\n\"{req.message}\"\n\n"
            f"💡 *Swipe-reply directly to this message or type:*\n"
            f"`/reply {user_id} <your message>`"
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_card, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to alert admin of feedback: {e}")

    return {"ok": True, "feedback_id": fb_id}

# --- WebRTC WebSocket Signaling Endpoint ---
@app.websocket("/ws/signaling")
async def websocket_signaling_endpoint(websocket: WebSocket):
    """
    Lightweight WebRTC Signaling Server.
    Authenticates via Telegram initData token parameter and routes SDP/ICE messages.
    Zero audio buffering in RAM: streams flow direct P2P or via STUN/TURN.
    """
    await websocket.accept()
    init_data = websocket.query_params.get("init_data") or ""
    user_info = validate_telegram_init_data(init_data)

    if not user_info:
        await websocket.send_json({
            "type": "diagnostic",
            "code": "AUTH_FAILED",
            "message": "Cryptographic authentication failed. Please reopen the Mini App."
        })
        await websocket.close(code=1008)
        return

    user_id = int(user_info.get("id") or user_info.get("user_id"))
    peer = await signaling_hub.register_peer(websocket, user_id)

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                await signaling_hub.handle_peer_message(peer, data)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket exception for user {user_id}: {e}")
    finally:
        await signaling_hub.unregister_peer(peer)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, workers=1)
