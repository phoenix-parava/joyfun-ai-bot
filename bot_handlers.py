"""
Aiogram 3 Telegram Bot Dispatcher & Handlers
Strictly enforces Control Plane Deduplication, Accept-Only Legal Gate, and Two-Way Feedback Relay.
"""

import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    MenuButtonWebApp,
    WebAppInfo,
    BotCommand
)
from config import (
    BOT_TOKEN,
    ADMIN_CHAT_ID,
    CREATOR_TELEGRAM_HANDLE,
    MINI_APP_URL
)
from database import (
    get_or_create_user,
    accept_terms,
    save_feedback,
    record_feedback_reply,
    get_user
)

logger = logging.getLogger("BotHandlers")

# Tracking reply context: {admin_chat_message_id: target_user_id}
admin_reply_context: dict[int, int] = {}
# Tracking pending user reply to admin: {user_id: True}
user_reply_state: dict[int, bool] = {}

def get_terms_markup() -> InlineKeyboardMarkup:
    """Renders the single Accept-Only button with zero decline option."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Accept & Continue", callback_data="accept_terms")]
        ]
    )

def get_open_app_markup() -> InlineKeyboardMarkup:
    """Renders single inline launch button for authenticated users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Open Communication App", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
    )

TERMS_NOTICE_TEXT = (
    "📜 **Mandatory User Agreement & Privacy Policy**\n\n"
    "Welcome to the secure peer-to-peer audio and text communication network.\n\n"
    "**Strict Privacy Terms:**\n"
    "• You must strictly **NEVER** share your personal Telegram ID, phone number, email address, physical location, photos, or files with anyone.\n"
    "• All peer connections are end-to-end and strictly anonymous.\n"
    "• If you voluntarily disclose personal contact information or identity details, the platform and bot assume **zero responsibility or liability**.\n\n"
    "Please accept the agreement below to continue:"
)

INFO_TEXT = (
    "ℹ️ **Platform Overview & Security Architecture**\n\n"
    "• **Decentralized Media**: Voice sessions utilize browser-native WebRTC peer-to-peer connections (RTCPeerConnection with Opus codec) via external STUN/TURN relays. Audio packets stream directly between peers and are never buffered or recorded on backend servers.\n\n"
    "• **Zero-Trust Identity**: Users are identified solely by chosen pseudonyms. Real Telegram IDs, usernames, and profile photos are never exposed to peers.\n\n"
    "• **Cryptographic Integrity**: Mini App sessions are authenticated server-side via HMAC-SHA256 signature validation of Telegram WebApp initial data.\n\n"
    "• **Multilingual AI Companion**: Provides voice and text interactions across regional code-switched, native, and global languages without loading local machine learning models into server memory.\n\n"
    f"For support or inquiries, use /feedback or contact @{CREATOR_TELEGRAM_HANDLE}."
)

async def setup_bot_commands(bot: Bot):
    """Registers strictly the four approved slash commands and persistent MenuButtonWebApp."""
    commands = [
        BotCommand(command="start", description="Check user agreement and launch application"),
        BotCommand(command="info", description="Platform overview and creator attribution"),
        BotCommand(command="feedback", description="Submit feedback or questions to administrator"),
        BotCommand(command="stop", description="Terminate active bot-level states"),
    ]
    try:
        await bot.set_my_commands(commands)
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open App",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )
        logger.info("Bot commands and persistent MenuButtonWebApp successfully registered.")
    except Exception as e:
        logger.warning(f"Could not set bot commands or menu button: {e}")

def register_handlers(dp: Dispatcher, bot: Bot):
    """Registers strictly deduplicated handlers with protect_content=True."""

    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        user_id = message.from_user.id
        user_name = message.from_user.first_name or message.from_user.username or ""
        user = await get_or_create_user(user_id, default_name=user_name)

        # Remove any lingering ReplyKeyboardMarkup cleanly without cluttering chat
        remove_kb = ReplyKeyboardRemove(remove_keyboard=True)
        try:
            temp_msg = await message.answer("🔒 Initializing secure session...", reply_markup=remove_kb)
            await temp_msg.delete()
        except Exception:
            pass

        if not user.get("terms_accepted_at"):
            await message.answer(
                TERMS_NOTICE_TEXT,
                reply_markup=get_terms_markup(),
                parse_mode="Markdown",
                protect_content=True
            )
            return

        welcome_text = (
            f"👋 Welcome back, **{user.get('pseudonym', 'Friend')}**!\n\n"
            f"• **Preferred Language:** {user.get('language', 'tanglish').title()}\n"
            f"• **Modality:** {user.get('modality', 'voice').title()}\n"
            f"• **Security Status:** End-to-End Anonymous\n\n"
            f"Tap below or use the persistent **Open App** button on your bottom-left to launch:"
        )
        await message.answer(
            welcome_text,
            reply_markup=get_open_app_markup(),
            parse_mode="Markdown",
            protect_content=True
        )

    @dp.callback_query(F.data == "accept_terms")
    async def callback_accept_terms(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        await accept_terms(user_id)
        await callback.answer("✅ Agreement accepted!")

        user = await get_user(user_id) or {}
        confirmation = (
            f"✅ **Terms Accepted!**\n\n"
            f"Your anonymous profile is ready. Tap below to launch the communication portal:"
        )
        try:
            await callback.message.edit_text(
                confirmation,
                reply_markup=get_open_app_markup(),
                parse_mode="Markdown"
            )
        except Exception:
            await callback.message.answer(
                confirmation,
                reply_markup=get_open_app_markup(),
                parse_mode="Markdown",
                protect_content=True
            )

    @dp.message(Command("info"))
    async def cmd_info(message: types.Message):
        await message.answer(
            INFO_TEXT,
            parse_mode="Markdown",
            protect_content=True
        )

    @dp.message(Command("stop"))
    async def cmd_stop(message: types.Message):
        user_id = message.from_user.id
        user_reply_state.pop(user_id, None)
        await message.answer(
            "🛑 All active bot states have been terminated.\n"
            "You can launch the communication app anytime via the button below:",
            reply_markup=get_open_app_markup(),
            protect_content=True
        )

    @dp.message(Command("feedback"))
    async def cmd_feedback(message: types.Message, command: CommandObject):
        user_id = message.from_user.id
        user = await get_or_create_user(user_id)
        feedback_text = (command.args or "").strip()

        if not feedback_text:
            user_reply_state[user_id] = True
            await message.answer(
                "💬 **Submit Feedback or Question:**\n\n"
                "Please send your message below, or type:\n"
                "`/feedback <your message here>`",
                parse_mode="Markdown",
                protect_content=True
            )
            return

        pseudonym = user.get("pseudonym", "Anonymous")
        email = user.get("email_address") if user.get("email_enabled") else "Not Enabled"
        lang = user.get("language", "tanglish")

        fb_id = await save_feedback(user_id, pseudonym, email or "Not Enabled", lang, feedback_text)
        user_reply_state.pop(user_id, None)

        await message.answer(
            "✅ **Feedback Received!**\n\n"
            "Your message has been securely delivered to the platform administration team. "
            "If a reply is required, you will receive it directly here.",
            parse_mode="Markdown",
            protect_content=True
        )

        # Notify Admin with formatted card
        if ADMIN_CHAT_ID:
            admin_card = (
                f"📬 **New User Feedback #{fb_id}**\n\n"
                f"• **Pseudonym:** `{pseudonym}`\n"
                f"• **Telegram ID:** `{user_id}`\n"
                f"• **Cloud Email:** `{email or 'Not Enabled'}`\n"
                f"• **Language:** `{lang}`\n\n"
                f"**Message:**\n\"{feedback_text}\"\n\n"
                f"💡 *Swipe-reply directly to this message or type:*\n"
                f"`/reply {user_id} <your message>`"
            )
            try:
                sent = await bot.send_message(ADMIN_CHAT_ID, admin_card, parse_mode="Markdown")
                admin_reply_context[sent.message_id] = user_id
            except Exception as e:
                logger.error(f"Failed to deliver feedback to admin {ADMIN_CHAT_ID}: {e}")

    @dp.message(Command("reply"))
    async def cmd_reply(message: types.Message, command: CommandObject):
        """Admin command: /reply <user_id> <message>"""
        if message.from_user.id != ADMIN_CHAT_ID:
            return

        args = (command.args or "").strip()
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("⚠️ Usage: `/reply <telegram_id> <message>`", parse_mode="Markdown")
            return

        try:
            target_id = int(parts[0])
            reply_content = parts[1].strip()
        except ValueError:
            await message.answer("⚠️ Invalid numeric Telegram ID.", parse_mode="Markdown")
            return

        try:
            user_msg = (
                f"🛡️ **Platform Support Response:**\n\n"
                f"{reply_content}\n\n"
                f"*(You can reply directly to this message to continue the conversation.)*"
            )
            await bot.send_message(target_id, user_msg, parse_mode="Markdown", protect_content=True)
            user_reply_state[target_id] = True
            await message.answer(f"✅ Reply delivered to user `{target_id}`.", parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ Failed to deliver reply to {target_id}: {e}")

    @dp.message()
    async def handle_regular_messages(message: types.Message):
        user_id = message.from_user.id

        # 1. Check if Admin is swipe-replying to a feedback card
        if user_id == ADMIN_CHAT_ID and message.reply_to_message:
            target_id = admin_reply_context.get(message.reply_to_message.message_id)
            if target_id:
                reply_text = message.text or "[Non-text response]"
                try:
                    user_msg = (
                        f"🛡️ **Platform Support Response:**\n\n"
                        f"{reply_text}\n\n"
                        f"*(You can reply directly to this message to continue the conversation.)*"
                    )
                    await bot.send_message(target_id, user_msg, parse_mode="Markdown", protect_content=True)
                    user_reply_state[target_id] = True
                    await message.answer(f"✅ Reply delivered to user `{target_id}`.", parse_mode="Markdown")
                    return
                except Exception as ex:
                    await message.answer(f"❌ Could not deliver to user `{target_id}`: {ex}")
                    return

        # 2. Check if user is replying to Admin support or has active feedback prompt
        if user_reply_state.get(user_id) or (message.reply_to_message and "Platform Support" in (message.reply_to_message.text or "")):
            user = await get_or_create_user(user_id)
            pseudonym = user.get("pseudonym", "Anonymous")
            email = user.get("email_address") if user.get("email_enabled") else "Not Enabled"
            lang = user.get("language", "tanglish")
            msg_text = message.text or "[Attachment/Non-text]"

            fb_id = await save_feedback(user_id, pseudonym, email or "Not Enabled", lang, msg_text)
            user_reply_state.pop(user_id, None)

            await message.answer(
                "✅ **Message Relayed to Support!**\n\n"
                "Our team has received your update and will respond shortly.",
                protect_content=True
            )

            if ADMIN_CHAT_ID:
                admin_card = (
                    f"📬 **User Follow-Up Reply #{fb_id}**\n\n"
                    f"• **Pseudonym:** `{pseudonym}`\n"
                    f"• **Telegram ID:** `{user_id}`\n\n"
                    f"**Message:**\n\"{msg_text}\"\n\n"
                    f"💡 *Swipe-reply to this message to answer.*"
                )
                try:
                    sent = await bot.send_message(ADMIN_CHAT_ID, admin_card, parse_mode="Markdown")
                    admin_reply_context[sent.message_id] = user_id
                except Exception as e:
                    logger.error(f"Failed to relay follow-up to admin: {e}")
            return

        # 3. Default redirect to Mini App
        user = await get_or_create_user(user_id)
        if not user.get("terms_accepted_at"):
            await message.answer(
                TERMS_NOTICE_TEXT,
                reply_markup=get_terms_markup(),
                parse_mode="Markdown",
                protect_content=True
            )
            return

        await message.answer(
            "🚀 All communication controls are centralized in the Telegram Mini App.\n"
            "Tap below to open:",
            reply_markup=get_open_app_markup(),
            protect_content=True
        )
