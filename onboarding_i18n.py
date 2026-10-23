"""
Joy Bot - Multilingual Localization Engine
Supports: English, Hinglish, Tanglish, Telugu, Malayalam, Kannada, Bengali, Marathi, Spanish.

Mandate:
- For Tanglish and Hinglish: System bot UI/buttons remain in English, conversational AI speaks Tanglish/Hinglish.
- For Telugu, Malayalam, Kannada, Bengali, Marathi, Spanish: Entire bot UI, settings, notices, and dialogues translate into their language.
"""

from typing import Dict, Any, Tuple, Optional
import urllib.parse

def get_ui_lang(user_or_lang, country_code: str = "") -> str:
    """
    Returns the system bot interface language.
    Mandate from Phoenix:
    - Never translate system bot UI purely by conversational dialect (Tanglish, Hinglish, Telugu, etc. speak with Joy in their dialect, but system bot UI remains clean English for India).
    - System bot UI translates by Country (e.g. Germany -> German, Spain -> Spanish, India/US/UK/Canada/Australia -> English) OR by explicit user system_lang setting!
    """
    if isinstance(user_or_lang, dict):
        sys_l = (user_or_lang.get("system_lang") or "").lower().strip()
        if sys_l and sys_l not in ("auto", "default", "none", ""):
            return sys_l
        c_code = (user_or_lang.get("country_code") or country_code or "").upper().strip()
    elif isinstance(user_or_lang, str):
        val = user_or_lang.lower().strip()
        if val in ("german", "de"):
            return "german"
        if val in ("spanish", "es"):
            return "spanish"
        if val in ("telugu", "malayalam", "kannada", "bengali", "marathi", "english"):
            if not country_code:
                return val
        c_code = (country_code or "").upper().strip()
    else:
        c_code = (country_code or "").upper().strip()

    if c_code == "DE":
        return "german"
    elif c_code == "ES":
        return "spanish"
    else:
        return "english"

def get_country_step_1_text(first_name: str) -> str:
    """Step 1 of 6: Country selection presented first when a new user joins."""
    return (
        f"🌍 **Step 1 of 6: Select Your Country / Location**\n\n"
        f"Hey **{first_name}**! 💖 Welcome to **Joy** — Your 24/7 AI Voice Companion.\n\n"
        f"Where are you located? This helps us calibrate local languages, timezones, and regional voice accents for your AI companion:\n\n"
        f"👇 **Tap your country below to start:**"
    )

def get_language_step_2_text(country_code: str, first_name: str) -> str:
    """Step 2 of 6: Language selection tailored to the chosen country."""
    code = (country_code or "OTHER").strip().upper()
    country_names = {
        "IN": "India 🇮🇳",
        "DE": "Germany 🇩🇪",
        "US": "United States 🇺🇸",
        "GB": "United Kingdom 🇬🇧",
        "CA": "Canada 🇨🇦",
        "AU": "Australia 🇦🇺",
        "AE": "UAE 🇦🇪",
        "SG": "Singapore 🇸🇬",
        "MY": "Malaysia 🇲🇾"
    }
    c_label = country_names.get(code, "your region 🌐")
    return (
        f"🗣️ **Step 2 of 6: Select Your Everyday Language**\n\n"
        f"Awesome, **{first_name}**! Location set to **{c_label}**.\n\n"
        f"Which language do you speak or prefer for chatting and 24/7 voice calls? Joy will adapt naturally to your dialect and slang:\n\n"
        f"👇 **Tap your preferred language below:**"
    )

def get_languages_keyboard_for_country(country_code: str, current_lang: str = "auto") -> dict:
    """Builds inline keyboard of languages optimized for the user's country."""
    code = (country_code or "OTHER").strip().upper()
    def mark(val):
        return "✓ " if current_lang == val else ""

    if code == "IN":  # India
        rows = [
            [
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"},
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"}
            ],
            [
                {"text": f"{mark('telugu')}💬 Telugu (తెలుగు)", "callback_data": "onboard_lang_telugu"},
                {"text": f"{mark('malayalam')}💬 Malayalam (മലയാളം)", "callback_data": "onboard_lang_malayalam"}
            ],
            [
                {"text": f"{mark('kannada')}💬 Kannada (ಕನ್ನಡ)", "callback_data": "onboard_lang_kannada"},
                {"text": f"{mark('bengali')}💬 Bengali (বাংলা)", "callback_data": "onboard_lang_bengali"}
            ],
            [
                {"text": f"{mark('marathi')}💬 Marathi (मराठी)", "callback_data": "onboard_lang_marathi"},
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"}
            ],
            [
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]
    elif code == "DE":  # Germany / Deutschland
        rows = [
            [
                {"text": f"{mark('german')}💬 Deutsch (German)", "callback_data": "onboard_lang_german"},
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"}
            ],
            [
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"},
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"}
            ],
            [
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]
    elif code in ("US", "GB", "CA", "AU", "NZ"):  # Western / English-dominant
        rows = [
            [
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"},
                {"text": f"{mark('spanish')}💬 Spanish (Español)", "callback_data": "onboard_lang_spanish"}
            ],
            [
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"},
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"}
            ],
            [
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]
    elif code in ("AE", "SA"):  # Middle East
        rows = [
            [
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"},
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"}
            ],
            [
                {"text": f"{mark('malayalam')}💬 Malayalam (മലയാളം)", "callback_data": "onboard_lang_malayalam"},
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"}
            ],
            [
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]
    elif code in ("SG", "MY"):  # South East Asia
        rows = [
            [
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"},
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"}
            ],
            [
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"},
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]
    else:  # Global / Other
        rows = [
            [{"text": f"{mark('auto')}🌐 Auto-Detect", "callback_data": "onboard_lang_auto"}],
            [
                {"text": f"{mark('english')}💬 English", "callback_data": "onboard_lang_english"},
                {"text": f"{mark('spanish')}💬 Spanish (Español)", "callback_data": "onboard_lang_spanish"}
            ],
            [
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "onboard_lang_hinglish"},
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "onboard_lang_tanglish"}
            ],
            [
                {"text": f"{mark('telugu')}💬 Telugu (తెలుగు)", "callback_data": "onboard_lang_telugu"},
                {"text": f"{mark('malayalam')}💬 Malayalam (മലയാളം)", "callback_data": "onboard_lang_malayalam"}
            ],
            [
                {"text": f"{mark('kannada')}💬 Kannada (ಕನ್ನಡ)", "callback_data": "onboard_lang_kannada"},
                {"text": f"{mark('bengali')}💬 Bengali (বাংলা)", "callback_data": "onboard_lang_bengali"}
            ],
            [
                {"text": f"{mark('marathi')}💬 Marathi (मराठी)", "callback_data": "onboard_lang_marathi"},
                {"text": "➕ Request Language", "callback_data": "onboard_lang_request"}
            ]
        ]

    return {"inline_keyboard": rows}

def get_gender_step_text(lang: str, first_name: str) -> str:
    """Step 3 of 6: Gender selection."""
    ui_lang = get_ui_lang(lang)
    if ui_lang == "telugu":
        return (
            f"👤 **Step 3 of 6: మీ జెండర్ ఎంచుకోండి**\n\n"
            f"సరైన కంపానియన్‌ని సెట్ చేయడానికి మీ జెండర్ ఎంచుకోండి:\n\n"
            f"• **👨 Male:** మీ కంపానియన్ గర్ల్‌ఫ్రెండ్ (Joy)\n"
            f"• **👩 Female:** మీ కంపానియన్ బాయ్‌ఫ్రెండ్ (Joy)\n\n"
            f"👇 **కింద ఎంచుకోండి:**"
        )
    elif ui_lang == "malayalam":
        return (
            f"👤 **Step 3 of 6: നിങ്ങളുടെ ജെൻഡർ തിരഞ്ഞെടുക്കുക**\n\n"
            f"ശരിയായ കമ്പാനിയനെ ലഭിക്കാൻ നിങ്ങളുടെ ജെൻഡർ തിരഞ്ഞെടുക്കുക:\n\n"
            f"• **👨 Male:** ഗേൾഫ്രണ്ട് (Joy)\n"
            f"• **👩 Female:** ബോയ്ഫ്രണ്ട് (Joy)\n\n"
            f"👇 **താഴെ തിരഞ്ഞെടുക്കുക:**"
        )
    elif ui_lang == "kannada":
        return (
            f"👤 **Step 3 of 6: ನಿಮ್ಮ ಲಿಂಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ**\n\n"
            f"• **👨 Male:** ಗರ್ಲ್‌ಫ್ರೆಂಡ್ (Joy)\n"
            f"• **👩 Female:** ಬಾಯ್‌ಫ್ರೆಂಡ್ (Joy)\n\n"
            f"👇 **ಕೆಳಗೆ ಆಯ್ಕೆಮಾಡಿ:**"
        )
    elif ui_lang == "bengali":
        return (
            f"👤 **Step 3 of 6: আপনার জেন্ডার নির্বাচন করুন**\n\n"
            f"• **👨 Male:** গার্লফ্রেন্ড (Joy)\n"
            f"• **👩 Female:** বয়ফ্রেন্ড (Joy)\n\n"
            f"👇 **নিচে নির্বাচন করুন:**"
        )
    elif ui_lang == "marathi":
        return (
            f"👤 **Step 3 of 6: आपले लिंग निवडा**\n\n"
            f"• **👨 Male:** गर्लफ्रेंड (Joy)\n"
            f"• **👩 Female:** बॉयफ्रेंड (Joy)\n\n"
            f"👇 **खाली निवडा:**"
        )
    elif ui_lang == "german":
        return (
            f"🎟️ **Joy Closed Beta — Prioritäts-Warteliste**\n\n"
            f"Hallo **{first_name}**! Deine Vorab-Registrierung ist erfolgreich gespeichert.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Dein Wartelisten-Rang:** `#{pos}`\n"
            f"👥 **Warteliste gesamt:** {total_waitlist}\n"
            f"🔒 **Beta-Status:** 50/50 Pioneer-Plätze belegt\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **Wann werden Plätze frei?**\n"
            f"• **72-Stunden-Auto-Pruning:** Wenn ein bestehender Pioneer 72 Stunden inaktiv ist, wird sein Platz automatisch an die Spitze der Warteliste vergeben!\n"
            f"• **3 Plätze überspringen:** Teile deinen Einladungslink mit Freunden! Jeder Freund, der sich anmeldet, bringt dich **3 Plätze** nach vorne!\n\n"
            f"🔗 **Dein persönlicher Einladungslink:**\n"
            f"`{ref_url}`"
        )
    elif ui_lang == "spanish":
        return (
            f"👤 **Paso 3 de 6: ¿Cuál es tu género?**\n\n"
            f"Para presentarte a la persona adecuada, selecciona tu género:\n\n"
            f"• **👨 Hombre:** Tu compañera será tu novia atenta (Joy)\n"
            f"• **👩 Mujer:** Tu compañero será tu novio protector (Joy)\n\n"
            f"👇 **Selecciona abajo:**"
        )
    else:
        return (
            f"👤 **Step 3 of 6: What is your gender?**\n\n"
            f"To introduce you to the right companion and persona, please select your gender:\n\n"
            f"• **👨 Male:** Companion is your supportive Girlfriend (Joy)\n"
            f"• **👩 Female:** Companion is your caring Boyfriend (Joy)\n\n"
            f"👇 **Please select below:**"
        )

def get_gender_step_keyboard(lang: str) -> dict:
    """Step 3 inline buttons."""
    ui_lang = get_ui_lang(lang)
    if ui_lang == "telugu":
        m_txt, f_txt = "👨 పురుషుడు (Male)", "👩 స్త్రీ (Female)"
    elif ui_lang == "malayalam":
        m_txt, f_txt = "👨 പുരുഷൻ (Male)", "👩 സ്ത്രീ (Female)"
    elif ui_lang == "kannada":
        m_txt, f_txt = "👨 ಪುರುಷ (Male)", "👩 ಮಹಿಳೆ (Female)"
    elif ui_lang == "bengali":
        m_txt, f_txt = "👨 পুরুষ (Male)", "👩 মহিলা (Female)"
    elif ui_lang == "marathi":
        m_txt, f_txt = "👨 पुरुष (Male)", "👩 महिला (Female)"
    elif ui_lang == "german":
        return (
            f"🎟️ **Joy Closed Beta — Prioritäts-Warteliste**\n\n"
            f"Hallo **{first_name}**! Deine Vorab-Registrierung ist erfolgreich gespeichert.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Dein Wartelisten-Rang:** `#{pos}`\n"
            f"👥 **Warteliste gesamt:** {total_waitlist}\n"
            f"🔒 **Beta-Status:** 50/50 Pioneer-Plätze belegt\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **Wann werden Plätze frei?**\n"
            f"• **72-Stunden-Auto-Pruning:** Wenn ein bestehender Pioneer 72 Stunden inaktiv ist, wird sein Platz automatisch an die Spitze der Warteliste vergeben!\n"
            f"• **3 Plätze überspringen:** Teile deinen Einladungslink mit Freunden! Jeder Freund, der sich anmeldet, bringt dich **3 Plätze** nach vorne!\n\n"
            f"🔗 **Dein persönlicher Einladungslink:**\n"
            f"`{ref_url}`"
        )
    elif ui_lang == "spanish":
        m_txt, f_txt = "👨 Hombre (Male)", "👩 Mujer (Female)"
    else:
        m_txt, f_txt = "👨 Male", "👩 Female"

    return {
        "inline_keyboard": [
            [
                {"text": m_txt, "callback_data": "onboard_gender_male"},
                {"text": f_txt, "callback_data": "onboard_gender_female"}
            ]
        ]
    }

def get_naming_step_text(lang: str, first_name: str, gender: str) -> str:
    """Step 5 of 6: Naming & Custom Word suggestions."""
    clean_lang = (lang or "auto").lower()
    partner = "Girlfriend" if gender == "male" else "Boyfriend"

    if clean_lang == "tanglish":
        return (
            f"🌸 **Step 5 of 6: Companion Peyar & Ungalukku Pudicha Varthaigal**\n\n"
            f"Ungaloda {partner}-ku enna peyar vaikiringa, **{first_name}**?\n\n"
            f"👉 **Companion peyarai chat-la type pannunga!**\n\n"
            f"💡 **Word Suggestions (Varthaigal):**\n"
            f"Joy ungalai enna solli koopidanum? (e.g. *Thalaiva, Macha, Pattu, Sweetheart, Bro*) — neenga chat-la suggest panna varthaigalai Joy kathu pesum! 🥰\n\n"
            f"*(Default-ah 'Joy' peyare podhum na keela button tap pannunga)*"
        )
    elif clean_lang == "hinglish":
        return (
            f"🌸 **Step 5 of 6: Companion Ka Naam & Apne Fav Words Chuniye**\n\n"
            f"Aap apne {partner} ka kya naam rakhna chahte hain, **{first_name}**?\n\n"
            f"👉 **Chat mein koi bhi naam type karein!**\n\n"
            f"💡 **Word Suggestions (Aapke Shabd):**\n"
            f"Joy aapko kya keh kar bulaye? (e.g. *Babu, Shona, Yaar, Sweetheart, Bro*) — jo bhi words ya nicknames aap chahte hain chat mein batayein, Joy wahi bolega! 🥰\n\n"
            f"*(Agar 'Joy' hi naam rakhna hai toh niche tap karein)*"
        )
    elif clean_lang == "telugu":
        return (
            f"🌸 **Step 5 of 6: కంపానియన్ పేరు మరియు మీ ఇష్టమైన పదాలు**\n\n"
            f"మీ కంపానియన్‌కి ఏ పేరు పెట్టాలనుకుంటున్నారు, **{first_name}**?\n\n"
            f"👉 **ఏదైనా పేరును చాట్‌లో టైప్ చేయండి!**\n\n"
            f"💡 **పదాల సూచన:** Joy మిమ్మల్ని ఏమని పిలవాలి? (ఉదా: *బంగారం, బ్రో, డియర్*) — మీరు సూచించిన పదాలను Joy నేర్చుకుంటుంది! 🥰\n\n"
            f"*(లేదా డిఫాల్ట్ 'Joy' ఉంచడానికి కింద ట్యాప్ చేయండి)*"
        )
    elif clean_lang == "malayalam":
        return (
            f"🌸 **Step 5 of 6: കമ്പാനിയന്റെ പേരും ഇഷ്ടമുള്ള വാക്കുകളും**\n\n"
            f"നിങ്ങളുടെ കമ്പാനിയന് എന്ത് പേരിടാനാണ് ആഗ്രഹം, **{first_name}**?\n\n"
            f"👉 **ചാറ്റിൽ ഏതെങ്കിലും പേര് ടൈപ്പ് ചെയ്യുക!**\n\n"
            f"💡 **വാക്കുകളുടെ നിർദ്ദേശം:** Joy നിങ്ങളെ എന്ത് വിളിക്കണം? (e.g. *മുത്തേ, ബ്രോ, ഡിയർ*) — ആ വാക്കുകൾ ചാറ്റിൽ പറയാം! 🥰\n\n"
            f"*(ഡിഫോൾട്ട് 'Joy' നിലനിർത്താൻ താഴെ ടാപ്പ് ചെയ്യുക)*"
        )
    elif clean_lang == "kannada":
        return (
            f"🌸 **Step 5 of 6: ಕಂಪಾನಿಯನ್ ಹೆಸರು ಮತ್ತು ಇಷ್ಟವಾದ ಪದಗಳು**\n\n"
            f"ನಿಮ್ಮ ಕಂಪಾನಿಯನ್‌ಗೆ ಯಾವ ಹೆಸರಿಡಲು ಬಯಸುತ್ತೀರಿ, **{first_name}**?\n\n"
            f"👉 **ಚಾಟ್‌ನಲ್ಲಿ ಯಾವುದೇ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ!**\n\n"
            f"💡 **ಪದಗಳ ಸಲಹೆ:** Joy ನಿಮ್ಮನ್ನು ಏನೆಂದು ಕರೆಯಬೇಕು? ನೀವು ಸಲಹೆ ನೀಡಿದ ಪದಗಳನ್ನು Joy ಬಳಸುತ್ತದೆ! 🥰\n\n"
            f"*(ಅಥವಾ 'Joy' ಹೆಸರನ್ನೇ ಮುಂದುವರಿಸಲು ಕೆಳಗೆ ಟ್ಯಾಪ್ ಮಾಡಿ)*"
        )
    elif clean_lang == "german":
        return (
            f"🎉 **Herzlichen Glückwunsch, {first_name}! Du bist ein offizieller Beta Pioneer!**\n"
            f"🎟️ **Pioneer-Slot #{slot_or_pos} von {beta_limit} gesichert!**\n\n"
            f"Du hast exklusiven Vorab-Zugang, um Joys 24/7 KI-Sprachbegleiterin und Live-Duplex-Anrufe vor dem offiziellen Start zu testen.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **72-Stunden-Aktivitätsregel (Automatisches Pruning):**\n"
            f"Pioneer-Plätze sind auf 50 aktive Tester begrenzt. Wenn dein Account **72 aufeinanderfolgende Stunden (3 Tage)** inaktiv bleibt (0 Anrufe/Nachrichten), vergibt Joy AI deinen Platz automatisch an die Warteliste! Bleib aktiv! 🔥\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Beta Pioneer & Bug-Hunter-Belohnungen:**\n"
            f"Hilf mit, Joy perfekt zu machen! Verdiene **Kostenlose VIP-Pässe**:\n\n"
            f"🛡️ **Kritischer Bug / Sicherheitslücke:**\n"
            f"• **Belohnung:** 🌟 **Lebenslanger kostenloser VIP-Pass**\n\n"
            f"⚡ **Audio-Lag / Verbindungsabbruch:**\n"
            f"• **Belohnung:** 🎟️ **1 bis 3 Monate kostenloser VIP-Pass**\n\n"
            f"💡 **Top-Feature-Vorschläge / Neue Wörter:**\n"
            f"• **Belohnung:** 🎁 **1 Monat kostenloser VIP-Pass**\n\n"
            f"🗣️ **Übersetzungsfehler & Dialekt-Mängel:**\n"
            f"• **Belohnung:** 🎖️ **Pioneer-Abzeichen + 2 Wochen VIP**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **Ein persönlicher Hinweis von Schöpfer Phoenix:**\n"
            f"\"*Hallo zusammen! Ich spreche nicht jeden regionalen Dialekt perfekt. Wenn du Übersetzungsfehler findest oder Joy neue Wörter beibringen möchtest, nutze bitte /feedback — dein Feedback macht Joy zur besten Begleiterin!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **Fehler oder Wörter melden:**\n"
            f"Tippe unten auf **💡 Send Feedback** oder tippe `/feedback` ein!"
        )
    elif clean_lang == "spanish":
        return (
            f"🌸 **Paso 5 de 6: Nombre de tu compañero y palabras personalizadas**\n\n"
            f"¿Cómo te gustaría llamar a tu compañero, **{first_name}**?\n\n"
            f"👉 **¡Escribe cualquier nombre en el chat ahora mismo!**\n\n"
            f"💡 **Sugerencia de palabras:** ¿Qué apodo quieres que use Joy contigo? (ej. *Cariño, Bro, Campeón*) — ¡sugiere tus palabras favoritas y Joy las aprenderá! 🥰\n\n"
            f"*(O toca abajo para mantener Joy)*"
        )
    else:
        return (
            f"🌸 **Step 5 of 6: Name Your Companion & Suggest Custom Words**\n\n"
            f"What would you like to call your companion, **{first_name}**?\n\n"
            f"👉 **Type any name in chat right now!** *(e.g. any custom name you like)*\n\n"
            f"💡 **Word Suggestions:** What nickname or words do you want Joy to call you? (e.g. *Champ, Bestie, Darling, Bro*) — suggest any words you like in chat and Joy will learn them! 🥰\n\n"
            f"*(Or tap the button below if you want to keep Joy)*"
        )

def get_bounty_notice_text(lang: str, first_name: str, slot_or_pos: int, beta_limit: int, owner_mask: str = "Joy-PHOENIX") -> str:
    """Closed Beta Pioneer Notice with 7-Day Bug Hunter & Feedback Mandate & Bounties."""
    clean_lang = (lang or "auto").lower()

    inactivity_warning_en = (
        "⚠️ **MANDATORY 7-DAY BUG HUNTER & FEEDBACK MANDATE:**\n"
        "• **7-Day Testing Window:** You are granted an active **7-Day (1-Week) Trial** to test all voice calls, chats, and features.\n"
        "• **Action Required:** Within these 7 days, you **MUST** report at least **1 bug, 1 feature suggestion, or constructive feedback** via `/feedback` or `/bug`.\n"
        "• ❌ **Removal Policy:** If you do **NOT** find a bug and do **NOT** submit any feedback or suggestion within 7 days, your Beta Pioneer status will be **automatically REMOVED and your slot revoked**!\n"
        "• 🌟 **Permanent VIP Reward:** Submitting any bug or helpful suggestion will permanently lock in your **Founder Pioneer Badge & Free Lifetime VIP**! 🔥"
    )

    inactivity_warning_ta = (
        "⚠️ **7-NAATKAL BUG HUNTER & FEEDBACK MANDATE (KANDIPAANA VITHI):**\n"
        "• **7-Naatkal Testing Kaalam:** Ungalukku Joy-oda Voice Calls, Chats matrum ellam features-ah test panna **7 Naatkal (1 Vaaram)** active trial tharapadugiradhu.\n"
        "• **Neenga Seiya Vendiyathu:** Indha 7 naatkalukkul, neenga kandippa oru **bug report, pudhu feature idea, illa constructive feedback-ah** `/feedback` or `/bug` vazhiya submit pannanum.\n"
        "• ❌ **Removal Policy (Slot Neekkam):** Neenga 7 naatkalukkul endha bug-um kandupidikavillai endraal, illa endha suggestion/feedback-um tharavillai endraal, ungaludaiya **Beta Pioneer Access automatic-ah REMOVE / CANCEL seiyappadum**!\n"
        "• 🌟 **Permanent VIP Reward:** Neenga oru bug report pannaal, Creator Phoenix ungalukku **Founder Pioneer Badge & Lifetime Free VIP** hamesha-ku lock panni tharuvaar! 🔥"
    )

    inactivity_warning_hi = (
        "⚠️ **7-DINO KA BUG HUNTER & FEEDBACK MANDATE (ZAROORI NIYAM):**\n"
        "• **7 Dino Ka Testing Time:** Aapko Joy ke 24/7 Voice Calls aur sabhi features test karne ke liye **7 Din (1 Hafta)** ka active trial mila hai.\n"
        "• **Zaroori Kaam:** In 7 dino ke andar, aapko kam se kam ek **bug report, feature suggestion, ya constructive feedback** `/feedback` ya `/bug` se bhejna HOGA.\n"
        "• ❌ **Removal Warning (Slot Radd Karna):** Agar aap 7 dino mein koi bug nahi dhoondhte aur koi suggestion/feedback nahi dete, toh aapka **Beta Pioneer Slot automatically REMOVE aur radd (cancel) kar diya jayega**!\n"
        "• 🌟 **Permanent VIP Reward:** Koi bhi bug dhoondhne ya suggestion dene par Creator Phoenix aapka **Founder Pioneer Badge & Lifetime Free VIP** hamesha ke liye lock kar denge! 🔥"
    )

    inactivity_warning_te = (
        "⚠️ **7-రోజుల బగ్ హంటర్ & ఫీడ్‌బ్యాక్ నిబంధన (తప్పనిసరి):**\n"
        "• **7-రోజుల టెస్టింగ్ సమయం:** Joy 24/7 వాయిస్ కాల్స్ మరియు అన్ని ఫీచర్లను పరీక్షించడానికి మీకు **7 రోజులు (1 వారం)** యాక్టివ్ ట్రయల్ లభించింది.\n"
        "• **తప్పనిసరి పని:** ఈ 7 రోజుల్లో మీరు కనీసం ఒక **బగ్ రిపోర్ట్, కొత్త ఫీచర్ సూచన లేదా ఫీడ్‌బ్యాక్** `/feedback` ద్వారా పంపాలి.\n"
        "• ❌ **తొలగింపు హెచ్చరిక:** మీరు 7 రోజుల్లో ఎటువంటి బగ్ లేదా సలహాలు ఇవ్వకపోతే, మీ **బీటా పయనీర్ స్లాట్ ఆటోమేటిక్‌గా తొలగించబడుతుంది (REMOVE)**!\n"
        "• 🌟 **శాశ్వత VIP బహుమతి:** బగ్ లేదా సలహా పంపిన వెంటనే మీకు **లైఫ్‌టైమ్ ఫ్రీ పయనీర్ VIP** లాక్ చేయబడుతుంది! 🔥"
    )

    inactivity_warning_ml = (
        "⚠️ **7-ദിവസത്തെ ബഗ് ഹണ്ടർ & ഫീഡ്‌ബാക്ക് നിബന്ധന:**\n"
        "• **7-ദിവസത്തെ ട്രയൽ:** Joy ഫീച്ചറുകൾ ടെസ്റ്റ് ചെയ്യാൻ നിങ്ങൾക്ക് **7 ദിവസം (1 ആഴ്ച)** സമയം ലഭിക്കുന്നു.\n"
        "• **ചെയ്യേണ്ട കാര്യം:** ഈ 7 ദിവസത്തിനകം ഒരു **ബഗ് റിപ്പോർട്ട് അല്ലെങ്കിൽ നിർദ്ദേശം** `/feedback` വഴി അയക്കണം.\n"
        "• ❌ **റിമൂവൽ മുന്നറിയിപ്പ്:** 7 ദിവസത്തിനകം ബഗ് റിപ്പോർട്ട് ചെയ്യുകയോ നിർദ്ദേശം നൽകുകയോ ചെയ്തില്ലെങ്കിൽ, നിങ്ങളുടെ **ബീറ്റാ സ്ലോട്ട് റദ്ദാക്കപ്പെടും (REMOVED)**!\n"
        "• 🌟 **ലൈഫ്‌ടൈം VIP:** ബഗ് റിപ്പോർട്ട് ചെയ്താൽ നിങ്ങൾക്ക് **ലൈഫ്‌ടൈം ഫ്രീ VIP** ലഭിക്കും! 🔥"
    )

    if clean_lang == "tanglish":
        return (
            f"🎉 **Congratulations, {first_name}! Neenga official-ah Beta Pioneer aagitinga!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"Public launch-ku munadi Joy-oda 24/7 Voice Calls matrum companion features-ah test panna ungaluku early access kidaichiruku.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_ta}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **BETA PIONEER & BUG HUNTER BOUNTIES**\n"
            f"Joy-ah perfect panna help pannunga! **Free VIP Passes** reward-ah vellunga:\n\n"
            f"🛡️ **Major Bug / Security Vulnerability / Exploit:**\n"
            f"• **Reward:** 🌟 **Lifetime Free VIP Pass** (Unlimited 24/7 Calls forever)\n\n"
            f"⚡ **Severe Audio Lag / Call Drop / Repeat Loop:**\n"
            f"• **Reward:** 🎟️ **1 to 3 Months Free VIP Pass**\n\n"
            f"💡 **Pudhu Feature Idea / Word Suggestion:**\n"
            f"• **Reward:** 🎁 **1 Month Free VIP Pass**\n\n"
            f"🗣️ **Language, Dialect & Slang Thappugal (Flaws):**\n"
            f"• **Reward:** 🎖️ **Pioneer Badge + 2 Weeks Free VIP**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **Creator Phoenix-oda Humble Note:**\n"
            f"\"*Friends! Enaku ellam regional languages-um 100% fluent-ah theriyaadhu, adhala Joy-oda colloquial phrasing, Tanglish/Hinglish translations, illa regional slang-la chinna thappu irukalam. Neenga edhavadhu language mistake, unnatural slang paatha, dayavusenju `/feedback` vazhiya sollunga — neenga tharum words & feedback Joy-ah semaya train panna help pannum!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **Varthaigal & Bugs Report Panna:**\n"
            f"Keela ulla **💡 Send Feedback** button-ah tap pannunga or `/feedback` type pannunga!"
        )
    elif clean_lang == "hinglish":
        return (
            f"🎉 **Badhai Ho, {first_name}! Aap Official Beta Pioneer Ban Gaye Hain!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"Public rollout se pehle Joy ke 24/7 Voice Calls aur Live Duplex companion ko test karne ka exclusive access aapko mila hai.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_hi}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **BETA PIONEER & BUG HUNTER BOUNTIES**\n"
            f"Joy ko behtar banane mein madad karein aur **Free VIP Passes** jeetein:\n\n"
            f"🛡️ **Critical Bug / Security Vulnerability / Exploit:**\n"
            f"• **Reward:** 🌟 **Lifetime Free VIP Pass** (Unlimited 24/7 Calls)\n\n"
            f"⚡ **Severe Audio Lag / Call Drop / AI Repeat Loop:**\n"
            f"• **Reward:** 🎟️ **1 to 3 Months Free VIP Pass**\n\n"
            f"💡 **Top Feature Suggestion / Naye Shabd:**\n"
            f"• **Reward:** 🎁 **1 Month Free VIP Pass**\n\n"
            f"🗣️ **Language, Dialect & Slang Ki Galtiyan:**\n"
            f"• **Reward:** 🎖️ **Pioneer Badge + 2 Weeks Free VIP**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **Creator Phoenix Ka Humble Note:**\n"
            f"\"*Doston! Mujhe har regional language poori tarah fluent nahi aati, isliye Joy ki Hinglish/Tanglish phrasing ya local slang mein kuch choti galtiyan ho sakti hain. Agar aapko koi language mistake, unnatural dialogue ya slang flaw mile, ya aap koi naya word sikhana chahein, please `/feedback` se batayein — aapka feedback Joy ko best banata hai!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **Shabd Ya Bug Report Karne Ke Liye:**\n"
            f"Niche **💡 Send Feedback** tap karein ya `/feedback` type karein!"
        )
    elif clean_lang == "telugu":
        return (
            f"🎉 **అభినందనలు, {first_name}! మీరు అధికారిక బీటా పయనీర్ అయ్యారు!**\n"
            f"🎟️ **పయనీర్ స్లాట్ #{slot_or_pos} of {beta_limit} లభించింది!**\n\n"
            f"పబ్లిక్ లాంచ్‌కి ముందే Joy 24/7 లైవ్ వాయిస్ కాల్స్‌ని పరీక్షించడానికి మీకు ప్రత్యేక యాక్సెస్ లభించింది.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_te}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **బీటా పయనీర్ & బగ్ హంటర్ బహుమతులు (ఉచిత VIP పాస్)**\n"
            f"🛡️ **తీవ్రమైన బగ్ / భద్రతా లోపం:** 🌟 **లైఫ్‌టైమ్ ఫ్రీ VIP పాస్**\n"
            f"⚡ **ఆడియో లాగ్ / కాల్ డ్రాప్:** 🎟️ **1 నుండి 3 నెలల ఉచిత VIP పాస్**\n"
            f"💡 **కొత్త ఫీచర్ సూచన / కొత్త పదాలు:** 🎁 **1 నెల ఉచిత VIP పాస్**\n"
            f"🗣️ **భాషా లోపాలు / వ్యాకరణ తప్పులు:** 🎖️ **2 వారాల ఉచిత VIP పాస్**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **నిర్మాత Phoenix నుండి చిన్న మాట:**\n"
            f"\"*నాకు అన్ని ప్రాంతీయ భాషలు సంపూర్ణంగా రావు, కాబట్టి Joy సంభాషణలలో ఏవైనా చిన్న తప్పులు ఉంటే లేదా కొత్త పదాలు నేర్పించాలనుకుంటే `/feedback` ద్వారా తెలియజేయండి!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **రిపోర్ట్ చేయడానికి:** కింద **💡 Send Feedback** ట్యాప్ చేయండి లేదా `/feedback` టైప్ చేయండి!"
        )
    elif clean_lang == "malayalam":
        return (
            f"🎉 **അഭിനന്ദനങ്ങൾ, {first_name}! നിങ്ങൾ ഔദ്യോഗിക ബീറ്റാ പയനിയർ ആയി!**\n"
            f"🎟️ **പയനിയർ സ്ലോട്ട് #{slot_or_pos} of {beta_limit} ലഭിച്ചു!**\n\n"
            f"പബ്ലിക് ലോഞ്ചിന് മുൻപ് Joy-യുടെ 24/7 ലൈവ് വോയ്‌സ് കോളുകൾ പരീക്ഷിക്കാൻ നിങ്ങൾക്ക് അവസരം ലഭിച്ചിരിക്കുന്നു.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_ml}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **ബഗ് ഹണ്ടർ ബഹുമതികൾ:**\n"
            f"🛡️ **ഗുരുതരമായ ബഗ്:** 🌟 **ലൈഫ്‌ടൈം സൗജന്യ VIP പാസ്**\n"
            f"⚡ **ഓഡിയോ ലാഗ് / കോൾ ഡ്രോപ്പ്:** 🎟️ **1 മുതൽ 3 മാസം സൗജന്യ VIP പാസ്**\n"
            f"💡 **പുതിയ ഫീച്ചർ / വാക്കുകൾ:** 🎁 **1 മാസം സൗജന്യ VIP പാസ്**\n\n"
            f"🚀 **റിപ്പോർട്ട് ചെയ്യാൻ:** `/feedback` ഉപയോഗിക്കുക!"
        )
    elif clean_lang == "german":
        return (
            f"🎉 **Herzlichen Glückwunsch, {first_name}! Du bist ein offizieller Beta Pioneer!**\n"
            f"🎟️ **Pioneer-Slot #{slot_or_pos} von {beta_limit} gesichert!**\n\n"
            f"Du hast exklusiven Vorab-Zugang, um Joys 24/7 KI-Sprachbegleiterin und Live-Duplex-Anrufe vor dem offiziellen Start zu testen.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_en}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Beta Pioneer & Bug-Hunter-Belohnungen:**\n"
            f"Hilf mit, Joy perfekt zu machen! Verdiene **Kostenlose VIP-Pässe**:\n\n"
            f"🛡️ **Kritischer Bug / Sicherheitslücke:**\n"
            f"• **Belohnung:** 🌟 **Lebenslanger kostenloser VIP-Pass**\n\n"
            f"⚡ **Audio-Lag / Verbindungsabbruch:**\n"
            f"• **Belohnung:** 🎟️ **1 bis 3 Monate kostenloser VIP-Pass**\n\n"
            f"💡 **Top-Feature-Vorschläge / Neue Wörter:**\n"
            f"• **Belohnung:** 🎁 **1 Monat kostenloser VIP-Pass**\n\n"
            f"🗣️ **Übersetzungsfehler & Dialekt-Mängel:**\n"
            f"• **Belohnung:** 🎖️ **Pioneer-Abzeichen + 2 Wochen VIP**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **Ein persönlicher Hinweis von Schöpfer Phoenix:**\n"
            f"\"*Hallo zusammen! Ich spreche nicht jeden regionalen Dialekt perfekt. Wenn du Übersetzungsfehler findest oder Joy neue Wörter beibringen möchtest, nutze bitte /feedback — dein Feedback macht Joy zur besten Begleiterin!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **Fehler oder Wörter melden:**\n"
            f"Tippe unten auf **💡 Send Feedback** oder tippe `/feedback` ein!"
        )
    elif clean_lang == "spanish":
        return (
            f"🎉 **¡Felicidades, {first_name}! Eres oficialmente un Pionero Beta!**\n"
            f"🎟️ **¡Ranura Pionera #{slot_or_pos} de {beta_limit} reclamada!**\n\n"
            f"Tienes acceso temprano exclusivo para probar las llamadas de voz 24/7 de Joy.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_en}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Recompensas para Cazadores de Errores:**\n"
            f"🛡️ **Vulnerabilidad Crítica:** 🌟 **Pase VIP Gratuito de por Vida**\n"
            f"⚡ **Lag de Audio / Corte:** 🎟️ **Pase VIP de 1 a 3 Meses**\n"
            f"💡 **Sugerencia de Función / Nuevas Palabras:** 🎁 **Pase VIP de 1 Mes**\n\n"
            f"🚀 **Para Reportar:** Escribe `/feedback` en cualquier momento."
        )
    else:
        return (
            f"🎉 **Congratulations, {first_name}! You're an Official Beta Pioneer!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"You have exclusive early access to test Joy's 24/7 AI Voice Companion and Live Duplex Calls before public rollout.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{inactivity_warning_en}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **BETA PIONEER & BUG HUNTER BOUNTIES**\n"
            f"Help us make Joy invincible! Earn **Free VIP Passes & Perks**:\n\n"
            f"🛡️ **Critical Vulnerability / Security Exploit:**\n"
            f"• **Reward:** 🌟 **Lifetime Free VIP Pass** (Unlimited 24/7 Voice Calls forever)\n\n"
            f"⚡ **Severe Audio Lag / Call Drop / AI Repeat Loop:**\n"
            f"• **Reward:** 🎟️ **1 to 3 Months Free VIP Pass**\n\n"
            f"💡 **Top Feature Suggestion / Custom Word Ideas:**\n"
            f"• **Reward:** 🎁 **1 Month Free VIP Pass** + Contributor Credit\n\n"
            f"🗣️ **Language, Dialect & Slang Flaws:**\n"
            f"• **Reward:** 🎖️ **Pioneer Badge + 2 Weeks Free VIP**\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 **A Humble Note from Creator (Phoenix):**\n"
            f"\"*Hey everyone! I don't speak every regional language and dialect fluently, so Joy's colloquial phrasing, Tanglish/Hinglish translations, or local slang might have small quirks. If you spot any language mistakes, unnatural phrases, or want to suggest custom words/phrases for Joy to say, please tell me via /feedback — your feedback directly shapes Joy into the best multilingual companion!*\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 **How to Report or Suggest Words:**\n"
            f"Tap **💡 Send Feedback** or type `/feedback` anytime!"
        )

def get_waitlist_card_text(lang: str, first_name: str, pos: int, total_waitlist: int, ref_url: str) -> str:
    """Localized Priority Waitlist Screen with 72-Hour Inactivity Rule Explanation."""
    ui_lang = get_ui_lang(lang)

    if ui_lang == "telugu":
        return (
            f"🎟️ **Joy క్లోజ్డ్ బీటా — ప్రాధాన్యత వెయిట్‌లిస్ట్**\n\n"
            f"హలో **{first_name}**! మీ రిజిస్ట్రేషన్ విజయవంతంగా పూర్తయింది.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **మీ వెయిట్‌లిస్ట్ ర్యాంక్:** `#{pos}`\n"
            f"👥 **మొత్తం వెయిట్‌లిస్ట్ యూజర్లు:** {total_waitlist}\n"
            f"🔒 **బీటా స్థితి:** 50/50 పయనీర్ స్లాట్‌లు నిండాయి\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **స్లాట్లు ఎప్పుడు ఓపెన్ అవుతాయి?**\n"
            f"• **72 గంటల ఆటో-ప్రూనింగ్:** ప్రస్తుత పయనీర్లలో ఎవరైనా 72 గంటల పాటు ఇనాక్టివ్‌గా ఉంటే, వారి స్లాట్ స్వయంచాలకంగా వెయిట్‌లిస్ట్‌లోని టాప్ యూజర్లకు బదిలీ అవుతుంది!\n"
            f"• **3 స్థానాలు ముందుకు దూకండి:** మీ ఆహ్వాన లింక్‌ను స్నేహితులతో పంచుకోండి! ప్రతి స్నేహితుడు చేరినప్పుడు మీ ర్యాంక్ **3 స్థానాలు** ముందుకు వెళ్తుంది!\n\n"
            f"🔗 **మీ పర్సనల్ ఆహ్వాన లింక్:**\n"
            f"`{ref_url}`"
        )
    elif ui_lang == "malayalam":
        return (
            f"🎟️ **Joy ക്ലോസ്ഡ് ബീറ്റാ — മുൻഗണനാ വെയ്റ്റ്‌ലിസ്റ്റ്**\n\n"
            f"ഹലോ **{first_name}**! നിങ്ങളുടെ പ്രീ-രജിസ്ട്രേഷൻ സേവ് ചെയ്തു.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **നിങ്ങളുടെ വെയ്റ്റ്‌ലിസ്റ്റ് സ്ഥാനം:** `#{pos}`\n"
            f"👥 **വെയ്റ്റ്‌ലിസ്റ്റിലുള്ള ആകെ ആളുകൾ:** {total_waitlist}\n"
            f"🔒 **സ്റ്റാറ്റസ്:** 50/50 സ്ലോട്ടുകൾ ഫുൾ ആണ്\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 **3 സ്ഥാനങ്ങൾ മുന്നിലേക്ക് ചാടാൻ:**\n"
            f"സുഹൃത്തുക്കളെ ക്ഷണിക്കുക! ഓരോ സുഹൃത്തും ചേരുമ്പോൾ നിങ്ങൾ **3 സ്ഥാനങ്ങൾ** മുന്നോട്ട് പോകും!\n\n"
            f"🔗 **നിങ്ങളുടെ ലിങ്ക്:**\n`{ref_url}`"
        )
    elif ui_lang == "german":
        return (
            f"🎟️ **Joy Closed Beta — Prioritäts-Warteliste**\n\n"
            f"Hallo **{first_name}**! Deine Vorab-Registrierung ist erfolgreich gespeichert.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Dein Wartelisten-Rang:** `#{pos}`\n"
            f"👥 **Warteliste gesamt:** {total_waitlist}\n"
            f"🔒 **Beta-Status:** 50/50 Pioneer-Plätze belegt\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **Wann werden Plätze frei?**\n"
            f"• **72-Stunden-Auto-Pruning:** Wenn ein bestehender Pioneer 72 Stunden inaktiv ist, wird sein Platz automatisch an die Spitze der Warteliste vergeben!\n"
            f"• **3 Plätze überspringen:** Teile deinen Einladungslink mit Freunden! Jeder Freund, der sich anmeldet, bringt dich **3 Plätze** nach vorne!\n\n"
            f"🔗 **Dein persönlicher Einladungslink:**\n"
            f"`{ref_url}`"
        )
    elif ui_lang == "spanish":
        return (
            f"🎟️ **Beta Cerrada de Joy — Lista de Espera Prioritaria**\n\n"
            f"¡Hola **{first_name}**! Tu perfil de pre-registro está guardado.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Tu posición en la cola:** `#{pos}`\n"
            f"👥 **Total en lista de espera:** {total_waitlist}\n"
            f"🔒 **Estado:** 50/50 Cupos Pioneros Llenos\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **¿Cómo avanzar?**\n"
            f"• **Poda de inactividad de 72h:** Si un usuario pionero pasa 3 días inactivo, su cupo se libera automáticamente para el #1 de la lista.\n"
            f"• **Salta 3 puestos:** ¡Comparte tu enlace de invitación! Por cada amigo registrado, avanzas **3 puestos** en la fila.\n\n"
            f"🔗 **Tu enlace de invitación:**\n`{ref_url}`"
        )
    else:
        return (
            f"🎟️ **Joy Closed Beta — Priority Waitlist**\n\n"
            f"Hey **{first_name}**! Your pre-registration profile is 100% saved.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📍 **Your Queue Position:** `#{pos}`\n"
            f"👥 **Total Waitlisted Users:** {total_waitlist}\n"
            f"🔒 **Closed Beta Status:** 50/50 Pioneer Slots Filled\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **How Pioneer Slots Open Up:**\n"
            f"• **72-Hour Inactivity Pruning:** Active pioneers who stay inactive (zero calls/chats) for 3 days automatically lose their slot to the #1 user on this waitlist!\n"
            f"• **Skip 3 Spots Forward:** Share your invite link! For every friend who pre-registers, your rank skips forward **3 spots** instantly!\n\n"
            f"🔗 **Your Personal Invite Link:**\n"
            f"`{ref_url}`\n\n"
            f"🔔 *We will notify you immediately the second a Pioneer Slot opens for you!*"
        )

def get_localized_settings_content(lang: str, profile_data: dict) -> Tuple[str, dict]:
    """Generates localized settings card text and keyboard buttons."""
    ui_lang = get_ui_lang(lang)

    first_name = profile_data.get("first_name", "Friend")
    username_str = profile_data.get("username_str", "")
    user_mask = profile_data.get("user_mask", "")
    country_display = profile_data.get("country_display", "")
    gender_str = profile_data.get("gender_str", "")
    lang_label = profile_data.get("lang_label", "")
    account_str = profile_data.get("account_str", "")
    vip_str = profile_data.get("vip_str", "")
    usage_str = profile_data.get("usage_str", "")
    data_sharing_str = profile_data.get("data_sharing_str", "")
    mem_str = profile_data.get("mem_str", "")
    bot_version = profile_data.get("bot_version", "v2.8.0")
    mini_app_version = profile_data.get("mini_app_version", "v2.0.0")
    portal_url = profile_data.get("portal_url", "")
    c_flag = profile_data.get("c_flag", "🌍")
    c_name_short = profile_data.get("c_name_short", "Country")
    c_name = profile_data.get("c_name", "Joy")
    data_sharing_active = profile_data.get("data_sharing_active", False)

    if ui_lang == "telugu":
        card_text = (
            f"⚙️ **సెట్టింగ్‌లు & ఖాతా సమాచారం**\n\n"
            f"👤 **వినియోగదారు ప్రొఫైల్:**\n"
            f"• **పేరు:** {first_name} ({username_str})\n"
            f"• **Joy మాస్క్ ID:** `{user_mask}` *(🎭 సురక్షితమైన గుర్తింపు)*\n"
            f"• **దేశం:** **{country_display}**\n"
            f"• **జెండర్:** **{gender_str}**\n"
            f"• **ప్రాధాన్య భాష:** **{lang_label}**\n\n"
            f"🔐 **ఖాతా & సభ్యత్వం:**\n"
            f"• **క్లౌడ్ ఖాతా:** {account_str}\n"
            f"• **VIP సభ్యత్వం:** {vip_str}\n"
            f"• **నేటి కోటా:** {usage_str}\n"
            f"• **డేటా ఎంపిక:** **{data_sharing_str}**\n"
            f"• **చాట్ జ్ఞాపకాలు:** {mem_str}\n\n"
            f"🏷️ **సిస్టమ్:** Bot `{bot_version}` • Mini App `{mini_app_version}`\n\n"
            f"👇 *సెట్టింగ్‌లను మార్చడానికి కింద ట్యాప్ చేయండి:*"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🌐 భాష: {lang_label}", "callback_data": "menu_language"},
                    {"text": f"👤 జెండర్: {gender_str}", "callback_data": "menu_toggle_gender"}
                ],
                [
                    {"text": "🔐 లాగిన్", "url": portal_url},
                    {"text": "⭐ Joy VIP పాస్", "callback_data": "menu_vip"}
                ],
                [
                    {"text": f"🌍 దేశం: {c_flag} {c_name_short}", "callback_data": "menu_country"},
                    {"text": f"✏️ పేరు మార్చు ({c_name})", "callback_data": "menu_rename_ai"}
                ],
                [
                    {"text": f"🛡️ గోప్యత: {'💡 20% తగ్గింపు' if data_sharing_active else '🔒 ప్రైవేట్'}", "callback_data": "menu_privacy"},
                    {"text": "📊 పరిమితులు & కోటా", "callback_data": "menu_quota"}
                ],
                [
                    {"text": "⬅️ మెయిన్ మెనూ", "callback_data": "menu_main"},
                    {"text": "❌ మూసివేయి", "callback_data": "menu_close"}
                ]
            ]
        }
    elif ui_lang == "malayalam":
        card_text = (
            f"⚙️ **സെറ്റിംഗ്സും അക്കൗണ്ടും**\n\n"
            f"👤 **പ്രൊഫൈൽ:**\n"
            f"• **പേര്:** {first_name} ({username_str})\n"
            f"• **Joy മാസ്ക് ID:** `{user_mask}` *(🎭 സുരക്ഷിത ഐഡി)*\n"
            f"• **രാജ്യം:** **{country_display}**\n"
            f"• **ലിംഗം:** **{gender_str}**\n"
            f"• **ഭാഷ:** **{lang_label}**\n\n"
            f"🔐 **അക്കൗണ്ട് വിവരങ്ങൾ:**\n"
            f"• **ക്ലൗഡ് അക്കൗണ്ട്:** {account_str}\n"
            f"• **VIP സ്റ്റാറ്റസ്:** {vip_str}\n"
            f"• **ഇന്നത്തെ ഉപയോഗം:** {usage_str}\n"
            f"• **ഡാറ്റ പ്രൈവസി:** **{data_sharing_str}**\n"
            f"• **ഓർമ്മകൾ:** {mem_str}\n\n"
            f"🏷️ **സിസ്റ്റം:** Bot `{bot_version}` • Mini App `{mini_app_version}`"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🌐 ഭാഷ: {lang_label}", "callback_data": "menu_language"},
                    {"text": f"👤 ലിംഗം: {gender_str}", "callback_data": "menu_toggle_gender"}
                ],
                [
                    {"text": "🔐 ലോഗിൻ", "url": portal_url},
                    {"text": "⭐ Joy VIP പാസ്", "callback_data": "menu_vip"}
                ],
                [
                    {"text": f"🌍 രാജ്യം: {c_flag} {c_name_short}", "callback_data": "menu_country"},
                    {"text": f"✏️ പേര് മാറ്റുക ({c_name})", "callback_data": "menu_rename_ai"}
                ],
                [
                    {"text": f"🛡️ പ്രൈവസി: {'💡 20% ഓഫർ' if data_sharing_active else '🔒 പ്രൈവറ്റ്'}", "callback_data": "menu_privacy"},
                    {"text": "📊 ഉപയോഗ പരിധി", "callback_data": "menu_quota"}
                ],
                [
                    {"text": "⬅️ മെയിൻ മെനു", "callback_data": "menu_main"},
                    {"text": "❌ ക്ലോസ്", "callback_data": "menu_close"}
                ]
            ]
        }
    elif ui_lang == "german":
        card_text = (
            f"⚙️ **Einstellungen & Account-Übersicht**\n\n"
            f"👤 **Benutzerprofil:**\n"
            f"• **Name:** {first_name} ({username_str})\n"
            f"• **Joy Mask-ID:** `{user_mask}` *(🎭 Geschützte Identität)*\n"
            f"• **Land:** **{country_display}**\n"
            f"• **Geschlecht:** **{gender_str}**\n"
            f"• **Gesprächssprache:** **{lang_label}**\n\n"
            f"🔐 **Account & Mitgliedschaft:**\n"
            f"• **Joy Cloud Account:** {account_str}\n"
            f"• **VIP-Mitgliedschaft:** {vip_str}\n"
            f"• **Heutiges Kontingent:** {usage_str}\n"
            f"• **Datenschutz:** **{data_sharing_str}**\n"
            f"• **Gedächtnis:** {mem_str}\n\n"
            f"🏷️ **System:** Bot `{bot_version}` • Mini App `{mini_app_version}`\n\n"
            f"👇 *Passe Einstellungen oder Optionen unten an:*"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🗣️ Sprache: {lang_label}", "callback_data": "menu_language"},
                    {"text": f"👤 Geschlecht: {gender_str}", "callback_data": "menu_toggle_gender"}
                ],
                [
                    {"text": "🖥️ Menüsprache", "callback_data": "menu_system_lang"},
                    {"text": f"🌍 Land: {c_flag} {c_name_short}", "callback_data": "menu_country"}
                ],
                [
                    {"text": "🔐 Anmelden", "url": portal_url},
                    {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
                ],
                [
                    {"text": f"✏️ Umbenennen ({c_name})", "callback_data": "menu_rename_ai"},
                    {"text": f"🛡️ Datenschutz: {'💡 20% Rabatt' if data_sharing_active else '🔒 Privat'}", "callback_data": "menu_privacy"}
                ],
                [
                    {"text": "📊 Kontingente & Limits", "callback_data": "menu_quota"},
                    {"text": "❌ Schließen", "callback_data": "menu_close"}
                ]
            ]
        }
    elif ui_lang == "spanish":
        card_text = (
            f"⚙️ **Ajustes y Cuenta**\n\n"
            f"👤 **Perfil de Usuario:**\n"
            f"• **Nombre:** {first_name} ({username_str})\n"
            f"• **ID Máscara Joy:** `{user_mask}` *(🎭 Identidad Protegida)*\n"
            f"• **País:** **{country_display}**\n"
            f"• **Género:** **{gender_str}**\n"
            f"• **Idioma:** **{lang_label}**\n\n"
            f"🔐 **Membresía:**\n"
            f"• **Cuenta Joy Cloud:** {account_str}\n"
            f"• **Membresía VIP:** {vip_str}\n"
            f"• **Cuota de Hoy:** {usage_str}\n"
            f"• **Privacidad:** **{data_sharing_str}**\n"
            f"• **Memoria:** {mem_str}\n\n"
            f"🏷️ **Sistema:** Bot `{bot_version}` • Mini App `{mini_app_version}`"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🌐 Idioma: {lang_label}", "callback_data": "menu_language"},
                    {"text": f"👤 Género: {gender_str}", "callback_data": "menu_toggle_gender"}
                ],
                [
                    {"text": "🖥️ Idioma del Menú", "callback_data": "menu_system_lang"},
                    {"text": f"🌍 País: {c_flag} {c_name_short}", "callback_data": "menu_country"}
                ],
                [
                    {"text": "🔐 Iniciar Sesión", "url": portal_url},
                    {"text": "⭐ Joy Pase VIP", "callback_data": "menu_vip"}
                ],
                [
                    {"text": f"✏️ Renombrar ({c_name})", "callback_data": "menu_rename_ai"},
                    {"text": f"🛡️ Privacidad: {'💡 20% Dcto' if data_sharing_active else '🔒 Privado'}", "callback_data": "menu_privacy"}
                ],
                [
                    {"text": "📊 Cuotas y Límites", "callback_data": "menu_quota"},
                    {"text": "❌ Cerrar", "callback_data": "menu_close"}
                ]
            ]
        }
    else:
        # Standard clean English (for English, Tanglish, Hinglish, and Fallback)
        card_text = (
            f"⚙️ **Settings & Account Hub**\n\n"
            f"👤 **User Profile:**\n"
            f"• **Name:** {first_name} ({username_str})\n"
            f"• **Joy Mask ID:** `{user_mask}` *(🎭 Protected Identity)*\n"
            f"• **Country:** **{country_display}**\n"
            f"• **Gender:** **{gender_str}**\n"
            f"• **Preferred Language:** **{lang_label}**\n\n"
            f"🔐 **Account & Membership:**\n"
            f"• **Joy Cloud Account:** {account_str}\n"
            f"• **VIP Membership:** {vip_str}\n"
            f"• **Today's Quota:** {usage_str}\n"
            f"• **Data Choices:** **{data_sharing_str}**\n"
            f"• **Chat Memory:** {mem_str}\n\n"
            f"🏷️ **System:** Bot `{bot_version}` • Mini App `{mini_app_version}`\n\n"
            f"👇 *Customize settings or manage your account below:*"
        )
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🗣️ Chat Language: {lang_label}", "callback_data": "menu_language"},
                    {"text": f"👤 Gender: {gender_str}", "callback_data": "menu_toggle_gender"}
                ],
                [
                    {"text": "🖥️ Bot Menu Language", "callback_data": "menu_system_lang"},
                    {"text": f"🌍 Country: {c_flag} {c_name_short}", "callback_data": "menu_country"}
                ],
                [
                    {"text": "🔐 Account Login", "url": portal_url},
                    {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
                ],
                [
                    {"text": f"✏️ Rename ({c_name})", "callback_data": "menu_rename_ai"},
                    {"text": f"🛡️ Privacy: {'💡 20% Off' if data_sharing_active else '🔒 Private'}", "callback_data": "menu_privacy"}
                ],
                [
                    {"text": "📊 Quotas & Limits", "callback_data": "menu_quota"},
                    {"text": "❌ Close", "callback_data": "menu_close"}
                ]
            ]
        }

    return card_text, keyboard
