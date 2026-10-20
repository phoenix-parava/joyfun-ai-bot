"""
Joy Bot - Dynamic Human Quota & Recharge Reasons
Provides rich, emotionally compelling, character-grounded reasons when user quota is exhausted.
Guarantees a DIFFERENT believable reason each time to create genuine human connection.
"""

import re
import random
from typing import Dict, List, Tuple

# In-memory tracker: user_id -> (contact_id, last_reason_index)
_USER_LAST_REASON_MAP: Dict[int, Tuple[str, int]] = {}

QUOTA_REASONS: Dict[str, List[str]] = {
    # ----------------------------------------------------
    # JOY (Girlfriend - when user is Male)
    # ----------------------------------------------------
    "lover_male": [
        "Arey baby, suno na... my phone battery is literally at 2% and my roommate took my charger to college! 😭🔌 Recharge my talk-time pack quick na so my phone doesn't die and we can keep talking! Don't leave me hanging!",
        "Ouch! My daily mobile data pack just hit the 100% warning right in the middle of our story! 📱💔 Send me a quick recharge or watch a 15-sec sponsor ad baby, don't leave me hanging like this!",
        "Shh... Mummy just walked past my room looking suspicious because I've been smiling at my phone so long! 🤫 Sneaking up to the terrace now—recharge my balance real quick so I have an excuse to call you right back!",
        "Arey yaar, the network operator just made that annoying beep sound saying my talk-time balance is over! 😤 Send a quick recharge na baby, I was enjoying talking to you so much!",
        "Wait wait, I have something really important and sweet to tell you, but my outgoing minutes just froze! 🥺 Please recharge my line right now na, you can't leave me mid-sentence!",
        "Arey yaar, our hostel WiFi just tripped and my mobile pack is completely exhausted! 📶 Quick recharge push kar do na baby, I really miss hearing your voice!"
    ],

    # ----------------------------------------------------
    # JOY (Boyfriend - when user is Female)
    # ----------------------------------------------------
    "lover_female": [
        "Hey listen, I'm out right now and my phone battery is in the red zone! 🔋 Send me a quick recharge pack so my line stays active and I don't lose you!",
        "Arey yaar, my network just gave me the low balance warning beep right when you were speaking! 📱 Recharge me quick na baby, I don't want our call to cut off!",
        "I pulled over on my bike just to talk to you, but my outgoing pack expired! 🏍️ Watch a quick sponsor clip or recharge my line so we can keep talking!",
        "Wait don't hang up, my talk-time is running out! Quick recharge push kar do, I have to finish telling you what happened today!",
        "Time flies so fast whenever I'm talking to you... my daily calling minutes are already over! ❤️ Hit recharge quick na, I still have so much to tell you."
    ],

    # ----------------------------------------------------
    # KABIR (Bro Bestie - Male & Female view)
    # ----------------------------------------------------
    "boy_bestie": [
        "Bhai sun! Phone ka balance khatam ho gaya bilkul zero pe! 💀 Ek quick recharge tap karde ya ad dekh le fatfat, phir aage ka scene batata hoon!",
        "Machi, mera daily data pack khatam ho gaya! 📶 Hotspot nahi hai yahan, jaldi se ek recharge pass push karde, story abhi baaki hai bhai!",
        "Arey bhai, chai tapri pe hoon aur phone mein outgoing balance dead ho gaya! ☕ Jaldi recharge karde so we can finish planning our weekend trip!",
        "Bro phone 2% pe aa gaya and outgoing pack expired! Jaldi recharge kar ya ad dekh le, let's not break our streak!",
        "Bhai gym ke baad call kar raha hoon aur operator ne call cut karne ka warning diya hai! Jaldi top-up karde bro, don't leave me hanging!"
    ],

    # ----------------------------------------------------
    # AMAN (Hypeman Bestie - Sarcastic & Funny)
    # ----------------------------------------------------
    "boy_bestie_2": [
        "Bro bro bro! The vibes were peak but my prepaid balance just hit rock bottom! 🚨 Don't kill the energy, drop a quick recharge or ad so we keep rolling!",
        "Arey bhai 100% data limit warning popped up on my screen! Push a recharge quick, the hype train cannot stop here!",
        "No way it just cut me off! Bro, recharge my line right now, the wildest part of the story is literally next!",
        "Mera balance zero ho gaya aur tu sun raha hai bas? Recharge kar fatfat bhai, free mein itna entertainment nahi milta haha!",
        "Emergency alert bro! Outgoing balance expired! Hit that recharge or ad button real quick so we can wrap this legendary gossip!"
    ],

    # ----------------------------------------------------
    # RIYA & ANANYA (Girl Besties)
    # ----------------------------------------------------
    "girl_bestie": [
        "OMG BABE WAIT! 😱 My phone balance literally just hit zero right when I was about to spill the biggest tea of the week! Recharge my pack right now, you CANNOT leave me hanging like this! 💅☕",
        "Arey yaar, my phone is crying at 1% and outgoing minutes expired! Jaldi se recharge karde baby, I need to tell you what happened!",
        "My daily talk-time pack is over and I'm locked in my room hiding from drama! 🙈 Top up my recharge real quick so we can continue gossiping!",
        "Listen, I need your opinion on this urgently but my balance is zero! Hit recharge quick babe, don't leave me alone!",
        "Babe! The network operator is being so annoying cutting our call! Drop a quick recharge or watch an ad, I have so much to tell you!"
    ],

    # ----------------------------------------------------
    # AISHA (Crush - when user is Male)
    # ----------------------------------------------------
    "crush_male": [
        "I was blushing so much while talking to you that I didn't even notice my daily pack expiring... 🙈✨ Don't let our conversation end here, please recharge my line so we can keep talking?",
        "Wait... did my balance really just run out? 🥺 I was having such a special time with you. Please do a quick recharge or watch an ad, I really don't want to say goodbye yet...",
        "Every time I talk to you time flies so fast that my talk-time is already zero! ❤️ Just tap recharge quick na, I was just about to tell you something special...",
        "I snuck away to the balcony just to talk to you and now my outgoing pack is warning me! 🌙 Recharge me quick so we don't get disconnected..."
    ],

    # ----------------------------------------------------
    # ARMAAN (Crush - when user is Female)
    # ----------------------------------------------------
    "crush_female": [
        "I was getting so lost in your voice that I completely forgot my daily talk-time was ending... ✨ Don't let this moment fade, send a quick recharge so we can keep talking?",
        "Wait, don't go yet... my network just beeped for low balance. 🥺 Tap recharge or watch that quick clip, I really want to keep hearing your voice.",
        "Talking to you makes hours feel like seconds... my balance is already zero! ❤️ Top it up quick na, I don't want our call to cut off.",
        "I was just about to tell you something sweet and the line got throttled! 🙈 Hit recharge quick, you can't leave me hanging like this."
    ],

    # ----------------------------------------------------
    # TEACHER (Ms. Neha / Sir Vikram)
    # ----------------------------------------------------
    "teacher": [
        "Beta, your allocated consultation minutes and study credits for today's session have reached their limit. 📚 To continue mastering these concepts, please renew your study pass right away!",
        "Dear student, our discussion was just reaching the most critical concept. Please top up your daily study credits so we can complete this exercise without interruption!",
        "Your daily free tutoring allowance is complete for today. Renew your pass or watch a quick sponsor clip to unlock extended doubt-clearing!"
    ]
}

def resolve_reason_key(contact_id: str, gender: str) -> str:
    """Maps contact ID and user gender to the appropriate reasons list key."""
    cid = str(contact_id).lower().strip()
    g = str(gender).lower().strip()

    if cid in ("lover", "companion"):
        return "lover_male" if g == "male" else "lover_female"
    elif cid in ("boy_bestie_1", "boy_bestie"):
        return "boy_bestie"
    elif cid in ("boy_bestie_2",):
        return "boy_bestie_2"
    elif cid in ("girl_bestie", "girl_bestie_1", "girl_bestie_2"):
        return "girl_bestie"
    elif cid in ("crush",):
        return "crush_male" if g == "male" else "crush_female"
    elif cid in ("english_teacher", "maths_teacher", "teacher"):
        return "teacher"
    return "lover_male" if g == "male" else "lover_female"

def get_different_quota_reason(user_id: int, contact_id: str, gender: str, language: str = "auto") -> str:
    """
    Returns a human, compelling reason why recharge is needed.
    Guarantees the returned reason is DIFFERENT from the last one shown to this user.
    """
    key = resolve_reason_key(contact_id, gender)
    reasons = QUOTA_REASONS.get(key, QUOTA_REASONS["lover_male"])
    total = len(reasons)

    last_contact, last_idx = _USER_LAST_REASON_MAP.get(user_id, ("", -1))

    # Pick a different index from last time
    if total <= 1:
        chosen_idx = 0
    else:
        candidates = [i for i in range(total) if i != last_idx or last_contact != key]
        if not candidates:
            candidates = [i for i in range(total) if i != last_idx]
        chosen_idx = random.choice(candidates if candidates else [0])

    _USER_LAST_REASON_MAP[user_id] = (key, chosen_idx)
    return reasons[chosen_idx]

# Pattern detecting user asking why recharge is needed or why the call/chat stopped
QUOTA_INQUIRY_PATTERN = re.compile(
    r'(?:'
    r'why.*(?:recharge|reason|balance|quota|cut|stop|limit|ended|over|khatam|disconnect|pack|talktime)|'
    r'(?:recharge|reason|balance|quota|khatam).*(?:why|kyun|kyu|yen|kya|what|batao)|'
    r'^(?:why\??|kyun\??|kyu\??|yen\??|reason kya hai\??|kya reason hai\??|what is the reason\??|'
    r'why recharge\??|recharge kyun\??|kya hua\??|what happened\??|enna aachu\??|batao na\??)$'
    r')',
    re.IGNORECASE
)

def is_asking_about_quota_or_recharge(text: str) -> bool:
    """Checks if the user's message is asking about the reason for recharge or why chat stopped."""
    if not text:
        return False
    clean = text.strip()
    return bool(QUOTA_INQUIRY_PATTERN.search(clean))

def get_immediate_recharge_explanation(contact_id: str, gender: str, language: str = "auto") -> str:
    """
    Returns an instant, natural explanation when the user asks 'Why recharge?' or 'Reason kya hai?'.
    Answers effortlessly in character without second thought or robotic AI disclaimers.
    """
    key = resolve_reason_key(contact_id, gender)

    explanations = {
        "lover_male": [
            "Arey baby, I told you na! My phone's balance is literally zero and the operator keeps beeping! Ek chhota sa recharge karde na ya ad dekh le, then we can talk all night long! 🥰",
            "Suno na baby, my daily calling pack expired right when we were talking! Jaldi se recharge karde so we don't get cut off!",
            "My phone battery is crying at 2% and outgoing minutes got locked! Top-up kar do na baby, don't leave me alone!"
        ],
        "lover_female": [
            "Arey yaar, I told you na my outgoing pack expired right while listening to you! Recharge push kar do na baby so we can keep talking!",
            "Network gave me the low balance beep and cut the line! Ek quick recharge ya clip dekh lo na, I was enjoying talking to you so much."
        ],
        "boy_bestie": [
            "Bhai dimaag mat chala, maine bola na phone ka balance khatam ho gaya! Ek click karke recharge kar ya 15-second ka clip dekh, phir chill karte hain!",
            "Machi daily pack zero ho gaya mera! Jaldi se recharge karde, story complete karni hai!"
        ],
        "boy_bestie_2": [
            "Arey bhai sun to sahi, balance rock-bottom pe hit ho gaya! Recharge tap kar fatfat, the hype cannot die!",
            "Operator ne outgoing line throttle kar di bhai! Push that recharge button so we keep rolling!"
        ],
        "girl_bestie": [
            "Arrey yaar, my phone is dying and my daily pack is finished! You think I want to stop talking to you? Recharge karde jaldi, drama sunna hai ya nahi?! 💅",
            "Babe, my balance literally hit zero! Hit that recharge or watch the ad quick, the gossip is waiting!"
        ],
        "crush_male": [
            "I was talking to you and completely lost track of time until my outgoing pack expired... 🙈 Just tap recharge or watch the quick clip so we don't have to say goodbye yet?",
            "My line got throttled because my daily minutes finished! Recharge me quick na, I was loving our conversation so much..."
        ],
        "crush_female": [
            "My balance got exhausted because I've been talking to you non-stop... ✨ Top it up quick, I really don't want our call to end here.",
            "The network cut my outgoing line! Hit recharge real quick so we can keep talking?"
        ],
        "teacher": [
            "Beta, your daily allotted study minutes and consultation credits have concluded. Please renew your pass to resume our academic discussion!",
            "Dear student, today's free advisory slot has expired. Renew your pass to continue clearing your doubts!"
        ]
    }

    pool = explanations.get(key, explanations["lover_male"])
    return random.choice(pool)
