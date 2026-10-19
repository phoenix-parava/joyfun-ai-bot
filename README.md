# 💖 Joy Bot — 24/7 Cloud AI Voice Companion & English Practice Buddy

Joy Bot is a cloud-native, high-speed AI Voice Companion on Telegram. Users can send voice notes anytime to vent, share their day, or practice fluent spoken English. Joy listens with native multi-modal audio understanding and speaks back with warm, natural, human-like neural voice notes.

---

## 🌟 Core Features

- 🎙️ **Voice In, Voice Out:** Directly understands Telegram voice notes (`.oga`/Opus) using Gemini 2.5 Flash native audio perception and replies with realistic neural voice audio.
- 👩‍🦰 **Expressive Indian Voices:** Powered by Microsoft Edge Neural TTS (`en-IN-NeerjaExpressiveNeural`, `en-IN-PrabhatNeural`, `hi-IN-SwaraNeural`).
- 💖 **Two Interactive Modes:**
  - **Best Friend Mode:** Deep emotional support, daily venting, jokes, and close friendship.
  - **English Practice Partner:** Gentle conversational practice, grammar tips, and interview coaching.
- 💰 **Built-in Freemium Monetization:**
  - Free users get 10 voice notes/day.
  - Automatic prompt to unlock **Joy VIP Pass (₹149/month)** when daily free limits are reached.
  - Interactive `/vip` command with UPI payment instructions.
- ☁️ **100% Cloud Autonomous:** Features an embedded async keep-alive HTTP health check on port `8080`, allowing 24/7 continuous hosting on free cloud platforms without touching laptop resources.

---

## 🚀 100% Free 24/7 Cloud Deployment Guide

You can deploy Joy Bot directly to the cloud for **₹0** without running anything on your laptop:

### Step 1: Create Your Bot Token
1. Open Telegram and search for [`@BotFather`](https://t.me/BotFather).
2. Send `/newbot`.
3. Choose a name: e.g. `Joy - My AI Friend`.
4. Choose a username: e.g. `joy_friend_ai_bot`.
5. Copy the HTTP API token provided by BotFather.

### Step 2: Deploy to Render (Free Web Service)
1. Push this repository to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial Joy Bot release"
   git remote add origin https://github.com/<your-username>/joy-bot.git
   git push -u origin main
   ```
2. Log into [Render.com](https://render.com) (free account).
3. Click **New +** -> **Web Service**.
4. Connect your `joy-bot` GitHub repository.
5. Set:
   - **Environment:** `Docker` (Render automatically uses the included `Dockerfile`).
   - **Instance Type:** `Free`.
6. Under **Environment Variables**, add:
   - `TELEGRAM_BOT_TOKEN` = `<your bot token from BotFather>`
   - `GEMINI_API_KEY` = `<your Gemini API key>`
   - `OWNER_ID` = `8747280850`
   - `PORT` = `8080`
7. Click **Deploy Web Service**!

Render will build the container, start the bot, and ping the `/health` endpoint to keep it alive 24/7. Your laptop can stay turned off!

---

## 🛠️ Local Testing (Optional)

If you ever want to test locally on your laptop:
```bash
/home/brandy/voice_chat_env/bin/python3 app.py
```
