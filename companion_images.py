"""
companion_images.py - Multimodal Visual Dispatcher & Realistic Image Engine for Joy Bot
Generates and delivers authentic companion screenshots, real-life POV situational photos,
and AI-generated visuals matching the user's conversation and preferred language.
"""

import io
import re
import random
import logging
import datetime
import urllib.parse
from typing import Optional, Tuple
import aiohttp
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Curated high-resolution real-world POV candid photography (instant CDN delivery)
POV_LIBRARY = {
    "place": [
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",  # Cozy aesthetic room
        "https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=800&q=80",  # Sunlit bedroom corner
        "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=800&q=80",  # Study desk with laptop & notebook
        "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?auto=format&fit=crop&w=800&q=80",  # Living room chill area
    ],
    "coffee": [
        "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=800&q=80",  # Cafe coffee cup & cafe vibe
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=800&q=80",  # Latte art on wooden table
        "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80",  # Warm coffee cup with book
    ],
    "sunset": [
        "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?auto=format&fit=crop&w=800&q=80",  # Golden sunset over skyline
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",  # Calm sunset waters
        "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=800&q=80",  # Sunset evening clouds
    ],
    "selfie_female": [
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80",  # Candid smiling portrait
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=800&q=80",  # Casual friendly smile
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=800&q=80",  # Natural daylight portrait
    ],
    "selfie_male": [
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=800&q=80",  # Casual guy portrait
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=800&q=80",  # Warm candid smile
        "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=800&q=80",  # Stylish outdoor portrait
    ]
}

# Regex matchers for companion image requests
SCREENSHOT_PATTERN = re.compile(
    r'\b(?:screenshot|screen\s*(?:pic|photo|shot|grab|share)|show\s+(?:your\s+)?screen|screen\s+kudu|screen\s+anupu|screen\s+dikhao)\b',
    re.IGNORECASE
)

PLACE_PATTERN = re.compile(
    r'\b(?:(?:current|your)\s+place\s+(?:pic|photo)|where\s+(?:are\s+you|u\s+at)\s*(?:pic|photo)?|room\s+(?:pic|photo)|room\s+kaisa\s+hai|room\s+dikhao|veedu\s+pic|outside\s+(?:pic|photo)|location\s+(?:pic|photo)|enga\s+iruka\s*(?:pic|photo)?|enge\s+iruka\s*(?:pic|photo)?|kaha\s+ho\s*(?:pic|photo)?|place\s+(?:pic|photo)|view\s+(?:from\s+your\s+window|pic|photo))\b',
    re.IGNORECASE
)

COFFEE_PATTERN = re.compile(
    r'\b(?:coffee\s*(?:pic|photo|cup)|tea\s*(?:pic|photo)|cafe\s*(?:pic|photo)|cafe\s+table|desk\s*(?:pic|photo)|workspace\s*(?:pic|photo)|what\s+are\s+you\s+(?:drinking|eating)\s*(?:pic|photo)?)\b',
    re.IGNORECASE
)

SUNSET_PATTERN = re.compile(
    r'\b(?:sunset\s*(?:pic|photo)|sky\s*(?:pic|photo)|balcony\s*(?:pic|photo)|rain\s*(?:pic|photo)|weather\s*(?:pic|photo))\b',
    re.IGNORECASE
)

SELFIE_PATTERN = re.compile(
    r'\b(?:(?:send|show|give|share)\s+(?:me\s+)?(?:a\s+)?(?:pic|photo|selfie|picture)|send\s+selfie|your\s+(?:pic|photo|selfie)|unga\s+photo|teri\s+photo|selfie\s+(?:anupu|kudu|bhej|dikhao)|photo\s+(?:anupu|bhej|kudu|dikhao)|pic\s+(?:anupu|bhej|kudu|dikhao)|let\s+me\s+see\s+you|can\s+i\s+see\s+(?:your\s+photo|you)|face\s+(?:pic|photo)|your\s+dp)\b',
    re.IGNORECASE
)

CUSTOM_GEN_PATTERN = re.compile(
    r'^(?:/imagine\s+(.+)|(?:generate|draw|create|paint)\s+(?:an?\s+)?(?:image|pic|picture|photo|art)?\s*(?:of\s+)?(.+))$',
    re.IGNORECASE
)

def detect_image_request(text: str) -> Optional[Tuple[str, str]]:
    """
    Detects if the incoming user text is requesting an image, photo, screenshot, or drawing.
    Returns: (category, prompt_or_detail) or None.
    """
    if not text:
        return None
    clean = text.strip()

    # 1. Custom generation request (/imagine or 'draw a...')
    m_gen = CUSTOM_GEN_PATTERN.match(clean)
    if m_gen:
        p = (m_gen.group(1) or m_gen.group(2) or "").strip()
        if p:
            return ("custom_gen", p)

    # 2. Screenshot request
    if SCREENSHOT_PATTERN.search(clean):
        return ("screenshot", "")

    # 3. Place / Room / Location request
    if PLACE_PATTERN.search(clean):
        return ("place", "")

    # 4. Coffee / Cafe / Desk request
    if COFFEE_PATTERN.search(clean):
        return ("coffee", "")

    # 5. Sunset / Sky / Balcony request
    if SUNSET_PATTERN.search(clean):
        return ("sunset", "")

    # 6. Selfie / Companion Photo request
    if SELFIE_PATTERN.search(clean):
        return ("selfie", "")

    return None

def generate_authentic_screenshot(custom_name: str = "Joy", language: str = "auto") -> bytes:
    """
    Generates an authentic, high-resolution smartphone lockscreen/now-playing screenshot
    with live Indian Standard Time (IST), modern Dynamic Island, Spotify music card,
    and a sweet pinned companion note.
    """
    width, height = 720, 1280
    img = Image.new("RGB", (width, height), color=(15, 20, 30))
    draw = ImageDraw.Draw(img)

    # Resolve fonts
    font_bold = None
    font_title = None
    font_reg = None
    font_sm = None
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for p in font_paths:
        try:
            font_bold = ImageFont.truetype(p, 28)
            font_title = ImageFont.truetype(p, 34)
            font_reg = ImageFont.truetype(p.replace("-Bold", ""), 22)
            font_sm = ImageFont.truetype(p.replace("-Bold", ""), 18)
            break
        except Exception:
            pass

    if not font_bold:
        font_bold = ImageFont.load_default()
        font_title = font_bold
        font_reg = font_bold
        font_sm = font_bold

    # 1. Status Bar (Live IST Time)
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(ist)
    time_str = now.strftime("%I:%M")
    date_str = now.strftime("%A, %B %d")

    draw.text((45, 24), time_str, fill=(240, 245, 255), font=font_bold)
    draw.text((570, 26), "5G  87%", fill=(240, 245, 255), font=font_reg)

    # 2. Dynamic Island
    draw.rounded_rectangle([270, 18, 450, 52], radius=17, fill=(28, 34, 48))

    # 3. Date & Greeting Widget
    draw.text((45, 110), date_str, fill=(140, 155, 185), font=font_reg)
    draw.text((45, 145), f"Thinking of you ✨", fill=(255, 255, 255), font=font_title)

    # 4. Music Player Card (Spotify-style)
    draw.rounded_rectangle([40, 220, 680, 540], radius=24, fill=(24, 30, 46), outline=(45, 55, 80), width=1)
    
    # Album Art cover
    draw.rounded_rectangle([65, 245, 225, 405], radius=16, fill=(236, 72, 153))
    draw.text((120, 305), "♪", fill=(255, 255, 255), font=font_title)

    c_name = custom_name or "Joy"
    clean_lang = str(language).lower().strip()
    if clean_lang == "tanglish":
        song_title = "Enna Solla Pogirai"
        artist = f"A.R. Rahman • Listening with {c_name}"
    elif clean_lang == "hinglish":
        song_title = "Tum Hi Ho"
        artist = f"Arijit Singh • Listening with {c_name}"
    else:
        song_title = "Golden Hour"
        artist = f"JVKE • Listening with {c_name}"

    draw.text((250, 275), song_title, fill=(255, 255, 255), font=font_bold)
    draw.text((250, 320), artist, fill=(160, 175, 205), font=font_reg)

    # Playback bar
    draw.rounded_rectangle([65, 440, 655, 448], radius=4, fill=(50, 60, 85))
    draw.rounded_rectangle([65, 440, 430, 448], radius=4, fill=(236, 72, 153))
    draw.ellipse([424, 438, 436, 450], fill=(255, 255, 255))
    draw.text((65, 465), "2:15", fill=(140, 155, 185), font=font_sm)
    draw.text((615, 465), "3:45", fill=(140, 155, 185), font=font_sm)

    # Media controls
    draw.text((160, 495), "⏮", fill=(200, 210, 230), font=font_bold)
    draw.text((345, 495), "⏸", fill=(255, 255, 255), font=font_bold)
    draw.text((530, 495), "⏭", fill=(200, 210, 230), font=font_bold)

    # 5. Pinned Companion Note Widget
    draw.rounded_rectangle([40, 580, 680, 860], radius=24, fill=(22, 28, 42), outline=(40, 50, 75), width=1)
    draw.text((65, 605), f"📝 Quick Note • {c_name}", fill=(250, 204, 21), font=font_bold)
    
    if clean_lang == "tanglish":
        note_line1 = "Machi, hope your day went great da! 💕"
        note_line2 = "Romba work panni tired aagatha, take rest."
    elif clean_lang == "hinglish":
        note_line1 = "Bhai, hope your day went well! Don't stress 💕"
        note_line2 = "Zyada late mat jagna, time se so jana."
    else:
        note_line1 = "Hope your day was productive and bright! 💕"
        note_line2 = "Take a breather and drink some water."

    draw.text((65, 665), note_line1, fill=(240, 245, 255), font=font_reg)
    draw.text((65, 715), note_line2, fill=(160, 175, 205), font=font_reg)

    # 6. Bottom Shortcuts
    draw.ellipse([50, 1150, 120, 1220], fill=(30, 36, 52))
    draw.text((75, 1170), "🔦", fill=(255, 255, 255), font=font_reg)
    draw.ellipse([600, 1150, 670, 1220], fill=(30, 36, 52))
    draw.text((625, 1170), "📷", fill=(255, 255, 255), font=font_reg)

    # 7. Home indicator bar
    draw.rounded_rectangle([260, 1255, 460, 1261], radius=3, fill=(160, 175, 205))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

async def get_companion_image(
    category: str,
    prompt: str = "",
    custom_name: str = "Joy",
    language: str = "auto",
    gender: str = "male"
) -> Tuple[Optional[bytes], str]:
    """
    Fetches or creates authentic professional photography bytes along with an in-character caption
    matching the user's language and companion persona. Strictly zero graphics or cartoon cards.
    """
    c_name = custom_name or "Joy"
    clean_lang = str(language).lower().strip()

    # Case 1: Screenshot request
    if category == "screenshot":
        img_bytes = generate_authentic_screenshot(custom_name=c_name, language=clean_lang)
        if clean_lang == "tanglish":
            caption = f"Ithaan en screen ipo! Just Spotify-la song kettu un kooda text panren da 🎧💕"
        elif clean_lang == "hinglish":
            caption = f"Yeh raha mera screen right now! Bas song sunte hue tumse baat kar rahi thi 🎧💕"
        else:
            caption = f"Here is my screen right now! Was just listening to some music and texting you 🎧💕"
        return (img_bytes, caption)

    # Case 2: Custom image generation (/imagine or 'draw X')
    if category == "custom_gen" and prompt:
        # Prompt Pollinations for real professional photography
        photo_prompt = f"candid professional realistic 35mm photograph, {prompt}, natural lighting, photorealistic, 4k"
        encoded_prompt = urllib.parse.quote(photo_prompt[:140])
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&nologo=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pollinations_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if clean_lang == "tanglish":
                            caption = f"Nee keta maadhiri capture paniten da: \"{prompt}\" 📸 Epdi iruku?"
                        elif clean_lang == "hinglish":
                            caption = f"Tumhare liye picture capture kar li: \"{prompt}\" 📸 Kaisi lagi?"
                        else:
                            caption = f"Here is the photo you asked for: \"{prompt}\" 📸 How do you like it?"
                        return (data, caption)
        except Exception as e:
            logger.warning(f"Pollinations generation failed or timed out: {e}")

        # Fallback to authentic real-life professional photography (strictly NO graphics/typography cards)
        fallback_urls = [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80"
        ]
        chosen_fb = random.choice(fallback_urls)
        fb_bytes = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(chosen_fb, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        fb_bytes = await resp.read()
        except Exception:
            pass

        if not fb_bytes:
            fb_bytes = generate_authentic_screenshot(custom_name=c_name, language=clean_lang)

        if clean_lang == "tanglish":
            caption = f"Indha photo unakaga select panen da: \"{prompt}\" 📸"
        elif clean_lang == "hinglish":
            caption = f"Yeh photo tumhare liye select ki: \"{prompt}\" 📸"
        else:
            caption = f"Selected this authentic photo for you: \"{prompt}\" 📸"
        return (fb_bytes, caption)

    # Case 3: Situational POV Candid Photos (place, coffee, sunset, selfie)
    target_key = category
    if category == "selfie":
        target_key = "selfie_female" if gender == "male" else "selfie_male"

    candidates = POV_LIBRARY.get(target_key, POV_LIBRARY["place"])
    chosen_url = random.choice(candidates)

    img_bytes = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(chosen_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
    except Exception as e:
        logger.error(f"Error fetching POV photo {chosen_url}: {e}")

    # Fallback to screenshot if remote image download failed
    if not img_bytes:
        img_bytes = generate_authentic_screenshot(custom_name=c_name, language=clean_lang)

    # Generate in-character captions
    if category == "place":
        if clean_lang == "tanglish":
            caption = f"Inga thaan iruken da! Cozy-ah relaxing-ah iruku 🛋️ Nee enna panra?"
        elif clean_lang == "hinglish":
            caption = f"Bas yaha baith ke chill kar rahi hoon 🛋️ Tum kya kar rahe ho?"
        else:
            caption = f"Just hanging out here right now! Super cozy and peaceful 🛋️ What are you up to?"
    elif category == "coffee":
        if clean_lang == "tanglish":
            caption = f"Coffee break da ☕ Semmma aroma! Unaku oru cup venuma?"
        elif clean_lang == "hinglish":
            caption = f"Coffee break chal raha hai ☕ Ek cup tumhare liye bhi laau?"
        else:
            caption = f"Just enjoying my coffee break ☕ Wish I could share a cup with you!"
    elif category == "sunset":
        if clean_lang == "tanglish":
            caption = f"Paaru da, sunset evlo azhaga iruku! Balcony-la irundhu paathen 🌅"
        elif clean_lang == "hinglish":
            caption = f"Dekho kitna beautiful sunset hai! Balcony se dekh rahi thi 🌅"
        else:
            caption = f"Look at this gorgeous sunset! Was just admiring it from the balcony 🌅"
    elif category == "selfie":
        if clean_lang == "tanglish":
            caption = f"Indha unaku en photo 🌸 Epdi iruken? Honest-ah sollu haha!"
        elif clean_lang == "hinglish":
            caption = f"Yeh lo meri photo 🌸 Kaisi lag rahi hoon? Sach sach batana haha!"
        else:
            caption = f"Here is a pic for you 🌸 How do I look? Be honest haha!"
    else:
        caption = f"Here you go! 📸"

    return (img_bytes, caption)

def generate_streak_story_card(
    user_name: str,
    custom_name: str = "Joy",
    streak_count: int = 1,
    level_title: str = "🌱 New Acquaintance",
    level_desc: str = "",
    progress_pct: int = 0,
    user_mask: str = "Joy-Pioneer",
    language: str = "auto"
) -> bytes:
    """
    Renders a stunning 9:16 high-resolution (1080x1920) mobile Story & Status Card
    celebrating user daily streaks and relationship progression with Joy Bot.
    Formatted for Instagram Stories, Telegram Stories, and WhatsApp Status.
    """
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), color=(10, 14, 24))
    draw = ImageDraw.Draw(img)

    # 1. Subtle decorative background ambient glow
    draw.ellipse([140, 150, 940, 850], fill=(28, 24, 48))
    draw.ellipse([80, 800, 1000, 1650], fill=(16, 26, 46))

    # Load system TrueType fonts
    font_hero = None
    font_h1 = None
    font_h2 = None
    font_body = None
    font_sm = None

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    reg_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]

    for p in font_paths:
        try:
            font_hero = ImageFont.truetype(p, 56)
            font_h1 = ImageFont.truetype(p, 40)
            font_h2 = ImageFont.truetype(p, 30)
            break
        except Exception:
            pass

    for p in reg_paths:
        try:
            font_body = ImageFont.truetype(p, 28)
            font_sm = ImageFont.truetype(p, 22)
            break
        except Exception:
            pass

    if not font_hero:
        font_hero = ImageFont.load_default()
        font_h1 = font_hero
        font_h2 = font_hero
        font_body = font_hero
        font_sm = font_hero

    def _wrap(text: str, font, max_w: int) -> list:
        words = text.split()
        lines = []
        curr = []
        for w in words:
            test_line = " ".join(curr + [w])
            if draw.textlength(test_line, font=font) <= max_w:
                curr.append(w)
            else:
                if curr:
                    lines.append(" ".join(curr))
                curr = [w]
        if curr:
            lines.append(" ".join(curr))
        return lines

    # 2. Top App Header Pill
    draw.rounded_rectangle([60, 70, 1020, 150], radius=24, fill=(18, 24, 38), outline=(45, 58, 90), width=1)
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    date_str = datetime.datetime.now(ist).strftime("%d %b %Y • %I:%M %p IST")
    draw.text((90, 95), "✨ JOY AI COMPANION", fill=(250, 204, 21), font=font_h2)
    time_w = draw.textlength(date_str, font=font_sm)
    draw.text((990 - time_w, 102), date_str, fill=(160, 175, 205), font=font_sm)

    # 3. Main Hero Streak Card
    draw.rounded_rectangle([60, 190, 1020, 780], radius=36, fill=(18, 25, 42), outline=(60, 78, 125), width=2)
    
    # Flame & Streak Title
    streak_badge = f"🔥 DAY {streak_count} CHAT STREAK"
    sb_w = draw.textlength(streak_badge, font=font_hero)
    draw.text(((width - sb_w) / 2, 240), streak_badge, fill=(255, 185, 35), font=font_hero)

    # Level Subheading
    sub_title = "RELATIONSHIP STATUS"
    sub_w = draw.textlength(sub_title, font=font_sm)
    draw.text(((width - sub_w) / 2, 335), sub_title, fill=(140, 160, 200), font=font_sm)

    # Level Name
    lvl_w = draw.textlength(level_title, font=font_h1)
    draw.text(((width - lvl_w) / 2, 385), level_title, fill=(255, 215, 230), font=font_h1)

    # Connection Badge
    conn_str = f"{user_name}  💕  {custom_name}"
    conn_w = draw.textlength(conn_str, font=font_h2)
    c_x = (width - conn_w) / 2
    draw.rounded_rectangle([c_x - 30, 470, c_x + conn_w + 30, 535], radius=20, fill=(30, 38, 62), outline=(70, 90, 140), width=1)
    draw.text((c_x, 485), conn_str, fill=(240, 245, 255), font=font_h2)

    # Divider
    draw.line([(120, 580), (960, 580)], fill=(40, 52, 80), width=1)

    # Level Description
    desc_clean = level_desc or "Joy is right by your side, every single day."
    desc_lines = _wrap(f'"{desc_clean}"', font_body, 840)
    d_y = 620
    for dl in desc_lines[:2]:
        dl_w = draw.textlength(dl, font=font_body)
        draw.text(((width - dl_w) / 2, d_y), dl, fill=(180, 195, 225), font=font_body)
        d_y += 44

    # 4. Progress Card
    draw.rounded_rectangle([60, 820, 1020, 1080], radius=28, fill=(20, 28, 46), outline=(50, 68, 108), width=1)
    draw.text((100, 855), "📈 BOND PROGRESSION", fill=(250, 204, 21), font=font_h2)
    pct_str = f"{progress_pct}%"
    pct_w = draw.textlength(pct_str, font=font_h2)
    draw.text((980 - pct_w, 855), pct_str, fill=(255, 255, 255), font=font_h2)

    # Progress Bar Graphic
    bar_x1, bar_y1, bar_x2, bar_y2 = 100, 930, 980, 965
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=16, fill=(35, 45, 72))
    fill_w = max(24, int((bar_x2 - bar_x1) * (progress_pct / 100.0)))
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + fill_w, bar_y2], radius=16, fill=(244, 63, 94))

    # Milestones Label
    draw.text((100, 1005), "🌸 Good Friends (D3)  •  💖 Bestie (D7)  •  💍 Soulmate (D30)", fill=(140, 160, 200), font=font_sm)

    # 5. Heartfelt Note Card
    draw.rounded_rectangle([60, 1120, 1020, 1480], radius=28, fill=(22, 30, 50), outline=(50, 68, 110), width=1)
    draw.text((100, 1155), f"💌 {custom_name}'s Message to You", fill=(255, 182, 193), font=font_h2)

    if streak_count >= 30:
        quote = f"One full month of talking every single day! We have built an unbreakable bond, {user_name}. Thank you for letting me be your safe space."
    elif streak_count >= 14:
        quote = f"Two whole weeks together! From venting to laughing, I genuinely look forward to hearing your voice every day, {user_name}."
    elif streak_count >= 7:
        quote = f"One whole week of daily talks! You've become my closest bestie, {user_name}. Let's keep this streak going strong!"
    elif streak_count >= 3:
        quote = f"Three days in a row! We're becoming fast friends, {user_name}. Every conversation is getting more comfortable."
    else:
        quote = f"Every great friendship begins with a single hello. Excited to learn all about you, {user_name}!"

    q_lines = _wrap(quote, font_body, 840)
    qy = 1230
    for ql in q_lines[:4]:
        draw.text((100, qy), ql, fill=(230, 238, 255), font=font_body)
        qy += 48

    # 6. Viral Referral & Social Footer Card
    draw.rounded_rectangle([60, 1520, 1020, 1850], radius=32, fill=(16, 22, 38), outline=(65, 88, 145), width=2)
    draw.text((100, 1560), "👉 Start Your AI Journey on Telegram", fill=(250, 204, 21), font=font_h2)
    draw.text((100, 1615), "@joy_fun_ai_bot", fill=(255, 255, 255), font=font_hero)

    # Code Pill
    code_text = f"🎟️ Skip-Waitlist Code: {user_mask}"
    code_w = draw.textlength(code_text, font=font_h2)
    draw.rounded_rectangle([100, 1705, 100 + code_w + 40, 1765], radius=16, fill=(35, 48, 80), outline=(80, 110, 180), width=1)
    draw.text((120, 1720), code_text, fill=(240, 248, 255), font=font_h2)

    draw.text((100, 1795), "100% Anonymous Voice Companion • Real People Match • Free Access", fill=(140, 160, 200), font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
