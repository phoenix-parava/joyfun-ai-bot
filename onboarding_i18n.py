"""
Joy Bot - Multilingual Localization for Onboarding, Word Suggestions & Bounty Notices
Supports: English, Hinglish, Tanglish, Telugu, Malayalam, Kannada, Bengali, Marathi, Spanish.
"""

from typing import Dict, Any

def get_country_step_text(lang: str, first_name: str, lang_title: str) -> str:
    lang = (lang or "auto").lower()
    if lang == "tanglish":
        return (
            f"🌍 **Step 2 of 6: Ungaloda Naadu (Country) Select Pannunga**\n\n"
            f"Super! Language set pannியாச்சு: **{lang_title}**.\n\n"
            f"**{first_name}**, neenga enga irukinga? Idhu voice accent matrum timing-ah correct-ah vaika help pannum:\n\n"
            f"👇 **Keela unga country-ah tap pannunga:**"
        )
    elif lang == "hinglish":
        return (
            f"🌍 **Step 2 of 6: Apna Desh (Country) Chuniye**\n\n"
            f"Great! Language set ho gayi: **{lang_title}**.\n\n"
            f"**{first_name}**, aap kahan rehte hain? Isse voice accent aur timings personalize karne mein help milti hai:\n\n"
            f"👇 **Niche apna country tap karein:**"
        )
    elif lang == "telugu":
        return (
            f"🌍 **Step 2 of 6: మీ దేశాన్ని ఎంచుకోండి**\n\n"
            f"భాష సెట్ చేయబడింది: **{lang_title}**.\n\n"
            f"**{first_name}**, మీరు ఎక్కడ ఉంటారు? వాయిస్ యాస మరియు సమయాన్ని సెట్ చేయడానికి కింద ఎంచుకోండి:\n\n"
            f"👇 **కింద మీ దేశాన్ని ట్యాప్ చేయండి:**"
        )
    elif lang == "malayalam":
        return (
            f"🌍 **Step 2 of 6: നിങ്ങളുടെ രാജ്യം തിരഞ്ഞെടുക്കുക**\n\n"
            f"ഭാഷ സജ്ജമാക്കി: **{lang_title}**.\n\n"
            f"**{first_name}**, നിങ്ങൾ എവിടെയാണ് താമസിക്കുന്നത്? വോയ്സ് ആക്സന്റും സമയവും കൃത്യമാക്കാൻ ഇത് സഹായിക്കും:\n\n"
            f"👇 **താഴെ നിങ്ങളുടെ രാജ്യം തിരഞ്ഞെടുക്കുക:**"
        )
    elif lang == "kannada":
        return (
            f"🌍 **Step 2 of 6: ನಿಮ್ಮ ದೇಶವನ್ನು ಆಯ್ಕೆಮಾಡಿ**\n\n"
            f"ಭಾಷೆ ಹೊಂದಿಸಲಾಗಿದೆ: **{lang_title}**.\n\n"
            f"**{first_name}**, ನೀವು ಎಲ್ಲಿದ್ದೀರಿ? ಧ್ವನಿ ಮತ್ತು ಸಮಯವನ್ನು ಹೊಂದಿಸಲು ಕೆಳಗೆ ಟ್ಯಾಪ್ ಮಾಡಿ:\n\n"
            f"👇 **ಕೆಳಗೆ ನಿಮ್ಮ ದೇಶವನ್ನು ಆಯ್ಕೆಮಾಡಿ:**"
        )
    elif lang == "bengali":
        return (
            f"🌍 **Step 2 of 6: আপনার দেশ নির্বাচন করুন**\n\n"
            f"ভাষা সেট করা হয়েছে: **{lang_title}**.\n\n"
            f"**{first_name}**, আপনি কোথায় থাকেন? ভয়েস ও সময় সেট করতে নিচে ট্যাপ করুন:\n\n"
            f"👇 **নিচে আপনার দেশ নির্বাচন করুন:**"
        )
    elif lang == "marathi":
        return (
            f"🌍 **Step 2 of 6: आपला देश निवडा**\n\n"
            f"भाषा सेट झाली आहे: **{lang_title}**.\n\n"
            f"**{first_name}**, आपण कुठे राहता? व्हॉइस आणि वेळ सेट करण्यासाठी खाली टॅप करा:\n\n"
            f"👇 **खाली आपला देश निवडा:**"
        )
    elif lang == "spanish":
        return (
            f"🌍 **Paso 2 de 6: Selecciona tu país**\n\n"
            f"Idioma configurado: **{lang_title}**.\n\n"
            f"¿Dónde te encuentras, **{first_name}**? Esto ayuda a personalizar acentos y horarios:\n\n"
            f"👇 **Toca tu país abajo:**"
        )
    else:
        return (
            f"🌍 **Step 2 of 6: Select Your Country**\n\n"
            f"Great! Language set to **{lang_title}**.\n\n"
            f"Where are you located, **{first_name}**? This helps personalize voice accents, timezone, and localized topics:\n\n"
            f"👇 **Tap your country below:**"
        )

def get_gender_step_text(lang: str, first_name: str) -> str:
    lang = (lang or "auto").lower()
    if lang == "tanglish":
        return (
            f"👤 **Step 3 of 6: Ungaloda Gender Enna?**\n\n"
            f"Ungaluku etha companion persona-va introduce panna unga gender-ah choose pannunga:\n\n"
            f"• **👨 Male:** Companion unga supportive Girlfriend (Joy)\n"
            f"• **👩 Female:** Companion unga caring Boyfriend (Joy)\n\n"
            f"👇 **Keela select pannunga:**"
        )
    elif lang == "hinglish":
        return (
            f"👤 **Step 3 of 6: Aapka Gender Kya Hai?**\n\n"
            f"Sahi companion persona introduce karne ke liye apna gender chuniye:\n\n"
            f"• **👨 Male:** Companion aapki caring Girlfriend (Joy) hogi\n"
            f"• **👩 Female:** Companion aapka caring Boyfriend (Joy) hoga\n\n"
            f"👇 **Niche select karein:**"
        )
    elif lang == "telugu":
        return (
            f"👤 **Step 3 of 6: మీ జెండర్ ఏంటి?**\n\n"
            f"సరైన కంపానియన్‌ని సెట్ చేయడానికి మీ జెండర్ ఎంచుకోండి:\n\n"
            f"• **👨 Male:** మీ కంపానియన్ గర్ల్‌ఫ్రెండ్ (Joy)\n"
            f"• **👩 Female:** మీ కంపానియన్ బాయ్‌ఫ్రెండ్ (Joy)\n\n"
            f"👇 **కింద ఎంచుకోండి:**"
        )
    elif lang == "malayalam":
        return (
            f"👤 **Step 3 of 6: നിങ്ങളുടെ ജെൻഡർ തിരഞ്ഞെടുക്കുക**\n\n"
            f"ശരിയായ കമ്പാനിയനെ ലഭിക്കാൻ നിങ്ങളുടെ ജെൻഡർ തിരഞ്ഞെടുക്കുക:\n\n"
            f"• **👨 Male:** ഗേൾഫ്രണ്ട് (Joy)\n• **👩 Female:** ബോയ്ഫ്രണ്ട് (Joy)\n\n"
            f"👇 **താഴെ തിരഞ്ഞെടുക്കുക:**"
        )
    elif lang == "kannada":
        return (
            f"👤 **Step 3 of 6: ನಿಮ್ಮ ಲಿಂಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ**\n\n"
            f"• **👨 Male:** ಗರ್ಲ್‌ಫ್ರೆಂಡ್ (Joy)\n• **👩 Female:** ಬಾಯ್‌ಫ್ರೆಂಡ್ (Joy)\n\n"
            f"👇 **ಕೆಳಗೆ ಆಯ್ಕೆಮಾಡಿ:**"
        )
    elif lang == "spanish":
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

def get_naming_step_text(lang: str, first_name: str, gender: str) -> str:
    lang = (lang or "auto").lower()
    partner = "Girlfriend" if gender == "male" else "Boyfriend"
    
    if lang == "tanglish":
        return (
            f"🌸 **Step 5 of 6: Companion Peyar & Ungalukku Pudicha Varthaigal**\n\n"
            f"Ungaloda {partner}-ku enna peyar vaikiringa, **{first_name}**?\n\n"
            f"👉 **Companion peyarai chat-la type pannunga!**\n\n"
            f"💡 **Word Suggestions (Varthaigal):**\n"
            f"Joy ungalai enna solli koopidanum? (e.g. *Thalaiva, Macha, Pattu, Sweetheart, Bro*) — neenga chat-la suggest panna varthaigalai Joy seekirame kathu pesum! 🥰\n\n"
            f"*(Default-ah 'Joy' peyare podhum na keela button tap pannunga)*"
        )
    elif lang == "hinglish":
        return (
            f"🌸 **Step 5 of 6: Companion Ka Naam & Apne Fav Words Chuniye**\n\n"
            f"Aap apne {partner} ka kya naam rakhna chahte hain, **{first_name}**?\n\n"
            f"👉 **Chat mein koi bhi naam type karein!**\n\n"
            f"💡 **Word Suggestions (Aapke Shabd):**\n"
            f"Joy aapko kya keh kar bulaye? (e.g. *Babu, Shona, Yaar, Sweetheart, Bro*) — jo bhi words ya nicknames aap chahte hain chat mein batayein, Joy wahi bolega! 🥰\n\n"
            f"*(Agar 'Joy' hi naam rakhna hai toh niche tap karein)*"
        )
    elif lang == "telugu":
        return (
            f"🌸 **Step 5 of 6: కంపానియన్ పేరు మరియు మీ ఇష్టమైన పదాలు**\n\n"
            f"మీ కంపానియన్‌కి ఏ పేరు పెట్టాలనుకుంటున్నారు, **{first_name}**?\n\n"
            f"👉 **ఏదైనా పేరును చాట్‌లో టైప్ చేయండి!**\n\n"
            f"💡 **పదాల సూచన:** Joy మిమ్మల్ని ఏమని పిలవాలి? (ఉదా: *బంగారం, బ్రో, డియర్*) — మీరు సూచించిన పదాలను Joy నేర్చుకుంటుంది! 🥰\n\n"
            f"*(లేదా డిఫాల్ట్ 'Joy' ఉంచడానికి కింద ట్యాప్ చేయండి)*"
        )
    elif lang == "malayalam":
        return (
            f"🌸 **Step 5 of 6: കമ്പാനിയന്റെ പേരും ഇഷ്ടമുള്ള വാക്കുകളും**\n\n"
            f"നിങ്ങളുടെ കമ്പാനിയന് എന്ത് പേരിടാനാണ് ആഗ്രഹം, **{first_name}**?\n\n"
            f"👉 **ചാറ്റിൽ ഏതെങ്കിലും പേര് ടൈപ്പ് ചെയ്യുക!**\n\n"
            f"💡 **വാക്കുകളുടെ നിർദ്ദേശം:** Joy നിങ്ങളെ എന്ത് വിളിക്കണം? (e.g. *മുത്തേ, ബ്രോ, ഡിയർ*) — ആ വാക്കുകൾ ചാറ്റിൽ പറയാം! 🥰\n\n"
            f"*(ഡിഫോൾട്ട് 'Joy' നിലനിർത്താൻ താഴെ ടാപ്പ് ചെയ്യുക)*"
        )
    elif lang == "kannada":
        return (
            f"🌸 **Step 5 of 6: ಕಂಪಾನಿಯನ್ ಹೆಸರು ಮತ್ತು ಇಷ್ಟವಾದ ಪದಗಳು**\n\n"
            f"ನಿಮ್ಮ ಕಂಪಾನಿಯನ್‌ಗೆ ಯಾವ ಹೆಸರಿಡಲು ಬಯಸುತ್ತೀರಿ, **{first_name}**?\n\n"
            f"👉 **ಚಾಟ್‌ನಲ್ಲಿ ಯಾವುದೇ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ!**\n\n"
            f"💡 **ಪದಗಳ ಸಲಹೆ:** Joy ನಿಮ್ಮನ್ನು ಏನೆಂದು ಕರೆಯಬೇಕು? ನೀವು ಸಲಹೆ ನೀಡಿದ ಪದಗಳನ್ನು Joy ಬಳಸುತ್ತದೆ! 🥰\n\n"
            f"*(ಅಥವಾ 'Joy' ಹೆಸರನ್ನೇ ಮುಂದುವರಿಸಲು ಕೆಳಗೆ ಟ್ಯಾಪ್ ಮಾಡಿ)*"
        )
    elif lang == "spanish":
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
    lang = (lang or "auto").lower()
    
    if lang == "tanglish":
        return (
            f"🎉 **Congratulations, {first_name}! Neenga official-ah Beta Pioneer aagitinga!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"Public launch-ku munadi Joy-oda 24/7 Voice Calls matrum companion features-ah test panna ungaluku early access kidaichiruku.\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **BETA PIONEER & BUG HUNTER BOUNTIES**\n"
            f"Joy-ah perfect panna help pannunga! **Free VIP Passes** reward-ah vellunga:\n\n"
            f"🛡️ **Major Bug / Security Vulnerability / System Exploit:**\n"
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
    elif lang == "hinglish":
        return (
            f"🎉 **Badhai Ho, {first_name}! Aap Official Beta Pioneer Ban Gaye Hain!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"Public rollout se pehle Joy ke 24/7 Voice Calls aur Live Duplex companion ko test karne ka exclusive access aapko mila hai.\n\n"
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
    elif lang == "telugu":
        return (
            f"🎉 **అభినందనలు, {first_name}! మీరు అధికారిక బీటా పయనీర్ అయ్యారు!**\n"
            f"🎟️ **పయనీర్ స్లాట్ #{slot_or_pos} of {beta_limit} లభించింది!**\n\n"
            f"పబ్లిక్ లాంచ్‌కి ముందే Joy 24/7 లైవ్ వాయిస్ కాల్స్‌ని పరీక్షించడానికి మీకు ప్రత్యేక యాక్సెస్ లభించింది.\n\n"
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
    else:
        return (
            f"🎉 **Congratulations, {first_name}! You're an Official Beta Pioneer!**\n"
            f"🎟️ **Pioneer Slot #{slot_or_pos} of {beta_limit} Claimed!**\n\n"
            f"You have exclusive early access to test Joy's 24/7 AI Voice Companion and Live Duplex Calls before public rollout.\n\n"
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
