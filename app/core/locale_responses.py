from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Final, Optional

BENGALI_RE: Final[re.Pattern[str]] = re.compile(r"[\u0980-\u09FF]")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").strip()


def text_looks_bengali(text: str) -> bool:
    return bool(BENGALI_RE.search(normalize_unicode(text)))


_BANGLISH_HINT: Final[re.Pattern[str]] = re.compile(
    r"\b(kholo|khul|koro|kor|dao|daw|gaan|gan|chalao|chalai|youtube|google|"
    r"ami|tumi|tomar|apni|accho|acchi|bolo|hok|koto|khobor|shono|shun|"
    r"shunchho|khul[oa]|pathao|pathai|whatsapp)\b",
    re.IGNORECASE,
)


def resolve_reply_language(setting: str, user_text: str) -> str:
    s = (setting or "auto").strip().lower()
    if s in {"bn", "bangla", "bengali"}:
        return "bn"
    if s in {"en", "english"}:
        return "en"
    if text_looks_bengali(user_text):
        return "bn"
    if _BANGLISH_HINT.search(user_text or ""):
        return "bn"
    return "en"


def infer_lang_from_stt_code(stt_language: str) -> str:
    low = (stt_language or "").strip().lower()
    return "bn" if low.startswith("bn") else "en"


def strip_mode_suffix(text: str) -> str:
    if "[mode:" in text:
        return text.split("[mode:", 1)[0].rstrip()
    return text


def _pick_variant(templates: tuple[str, ...], seed: str) -> str:
    if not templates:
        return ""
    h = 0
    for i, c in enumerate(seed or "x"):
        h = (h * 131 + ord(c) + i) & 0xFFFFFFFF
    return templates[h % len(templates)]


def feedback_prefix(intent: str, confidence: float, lang: str, *, seed: str = "") -> str:
    """Human-like acknowledgements; empty when the main line already carries the tone."""
    s = seed or str(confidence)
    if lang == "bn":
        if intent.startswith("youtube_") or intent.startswith("chitchat_") or intent == "desktop_open":
            return ""
        if intent == "greeting":
            return ""
        if intent == "fallback":
            return ""
        if confidence >= 0.85:
            return _pick_variant(
                (
                    "ঠিক আছে।",
                    "হ্যাঁ।",
                    "চলছে।",
                    "বুঝেছি।",
                    "চিন্তা করো না।",
                    "আমি সাহায্য করার জন্য আছি।",
                ),
                s,
            )
        if confidence >= 0.7:
            return _pick_variant(
                ("ঠিক আছে।", "কাজ করছি।", "চেষ্টা করছি।"),
                s,
            )
        return _pick_variant(
            ("একটু নিশ্চিত হতে হবে, তবু…", "চেষ্টা করছি…", "ধরার চেষ্টা করছি…"),
            s,
        )
    if intent.startswith("youtube_") or intent.startswith("chitchat_") or intent == "desktop_open":
        return ""
    if intent == "greeting":
        return ""
    if intent == "fallback":
        return ""
    if confidence >= 0.9:
        return _pick_variant(
            ("Sounds good.", "On it.", "Got it.", "Sure thing."),
            s,
        )
    if confidence >= 0.7:
        return _pick_variant(
            ("Working on it.", "Okay.", "You got it."),
            s,
        )
    return _pick_variant(
        ("Let me see…", "Let me try that…", "One moment…"),
        s,
    )


def format_time_bn(now: datetime.datetime | None = None) -> str:
    dt = now or datetime.datetime.now()
    return f"{dt.strftime('%I:%M %p')}, {dt.strftime('%d %B %Y')}"


def looks_conversational_soft(q: str, ql: str) -> bool:
    """Light chit-chat without obvious task verbs (for softer unknown handling)."""
    if len(ql) > 120:
        return False
    task_markers = (
        "youtube",
        "ইউটিউব",
        "google",
        "গুগল",
        "open",
        "search",
        "play",
        "খুল",
        "সার্চ",
        "গান",
        "alarm",
        "weather",
        "battery",
        "notepad",
        "সময়",
        "সময়",
        "টাইম",
        "time",
        "jarvis",
        "জারভিস",
    )
    if any(m in ql for m in task_markers if m.isascii()) or any(m in q for m in task_markers if not m.isascii()):
        return False
    casual_en = (
        "thanks",
        "thank you",
        "good morning",
        "good night",
        "good afternoon",
        "how are you",
        "how're you",
        "goodbye",
        "see you",
        "you there",
        "hear me",
        "listening",
    )
    casual_bn = (
        "ধন্যবাদ",
        "শুভ",
        "কেমন",
        "বিদায়",
        "হ্যাঁ",
        "আচ্ছা",
        "ঠিক আছে",
        "হ্যালো",
        "হাই",
        "শুন",
        "আছো",
        "আছেন",
        "কি খবর",
        "দুঃখিত",
    )
    if any(c in ql for c in casual_en):
        return True
    return any(c in q for c in casual_bn)


def classify_conversational_message(q: str, ql: str) -> Optional[str]:
    """
    Non-task conversational turns. Return intent key for system.chitchat, or None.
    """
    if len(ql) > 160:
        return None

    if any(x in ql for x in ("thank", "thanks", "thank you", "thx")):
        return "chitchat_thanks"
    if any(x in q for x in ("ধন্যবাদ", "শুক্রিয়া")):
        return "chitchat_thanks"

    if any(x in ql for x in ("how are you", "how r you", "how're you", "what's up", "sup ")):
        return "chitchat_how_are_you"
    if any(x in q for x in ("কেমন আছ", "কেমন আছেন", "কিরে", "কি খবর")):
        return "chitchat_how_are_you"
    if any(x in q for x in ("কী করছো", "কি করছো", "কী করছ", "কি করছ", "কি অবস্থা")):
        return "chitchat_smalltalk"

    if any(x in ql for x in ("good morning", "good afternoon", "good evening", "good night")):
        return "chitchat_greeting_time"
    if any(x in q for x in ("সুপ্রভাত", "শুভ সকাল", "শুভ রাত্রি", "নমস্কার")):
        return "chitchat_greeting_time"

    if any(x in ql for x in ("can you hear", "are you there", "you listening", "do you hear")):
        return "chitchat_listening_check"
    if any(x in q for x in ("শুনতে পাচ্ছ", "শুনছ", "আছো তুমি", "আছেন")):
        return "chitchat_listening_check"

    if any(x in ql for x in ("bye", "goodbye", "see you", "later", "take care")):
        return "chitchat_bye"
    if any(x in q for x in ("বিদায়", "আল্লাহ হাফেজ", "আসছি")):
        return "chitchat_bye"

    if ql.strip() in {"ok", "okay", "yes", "yeah", "yep", "sure"}:
        return "chitchat_ack"
    if q.strip() in {"ঠিক আছে", "হ্যাঁ", "জি", "আচ্ছা"}:
        return "chitchat_ack"

    if "love you" in ql or "appreciate" in ql:
        return "chitchat_warm"
    if "ভালোবাসি" in q or "পছন্দ" in q:
        return "chitchat_warm"

    return None


def greeting_response(user_text: str, lang: str) -> str:
    qn = normalize_unicode(user_text).strip()
    if lang == "bn":
        if qn in ("হাই", "হি"):
            return "হ্যালো, আমি তোমার কথা শুনতে পাচ্ছি। কী করতে চাও?"
        return _pick_variant(
            (
                "হ্যালো, আমি জারভিস—তোমার কী সাহায্য লাগবে? আমি সাহায্য করার জন্য আছি।",
                "হ্যাঁ, শুনছি। কী করতে চাও?",
                "আমি এখানে আছি—চিন্তা করো না, বলো কী করবো।",
            ),
            qn,
        )
    if qn.lower() in {"hi", "hey", "hello"}:
        return "Hi—I'm listening. What would you like to do?"
    return _pick_variant(
        ("Hey—I'm Jarvis. What can I do for you?", "Hi there! I'm here to help."),
        qn,
    )


def chitchat_response(intent_key: str, lang: str) -> str:
    if lang == "bn":
        m = {
            "chitchat_thanks": _pick_variant(
                (
                    "স্বাগতম। তোমার আর কিছু লাগলে বলো।",
                    "কোনো কথা না—চিন্তা করো না, আমি তো আছি।",
                    "তোমাকে সাহায্য করতে পেরে ভালো লাগল।",
                ),
                intent_key,
            ),
            "chitchat_how_are_you": _pick_variant(
                (
                    "আমি ভালো আছি। তুমি কী করতে চাও?",
                    "ভালোই—তুমি বলো, আজ কী করবো?",
                ),
                intent_key,
            ),
            "chitchat_smalltalk": _pick_variant(
                (
                    "আমি এখানে আছি—তুমি কী করতে চাও?",
                    "ভালো চলছে। বলো, কী সাহায্য লাগবে?",
                ),
                intent_key,
            ),
            "chitchat_greeting_time": _pick_variant(
                (
                    "আপনাকে শুভেচ্ছা! আমি জারভিস—কিভাবে সাহায্য করব?",
                    "শুভ দিন! কী করতে চান বলুন।",
                ),
                intent_key,
            ),
            "chitchat_listening_check": _pick_variant(
                (
                    "হ্যাঁ, আমি তোমার কথা পরিষ্কারভাবে শুনতে পাচ্ছি। বলো কী করতে হবে।",
                    "জি, শুনছি—একদম পরিষ্কার। বলো।",
                    "শুনতে পাচ্ছি, চিন্তা করো না।",
                ),
                intent_key,
            ),
            "chitchat_bye": _pick_variant(
                (
                    "বিদায়! দরকার হলে আবার ডাকবেন।",
                    "আল্লাহ হাফেজ—পরে কথা হবে।",
                ),
                intent_key,
            ),
            "chitchat_ack": _pick_variant(
                (
                    "ঠিক আছে, আমি রেডি। আর কিছু?",
                    "জি, বলুন কী করব।",
                ),
                intent_key,
            ),
            "chitchat_warm": _pick_variant(
                (
                    "আপনার কথা শুনে ভালো লাগল। আমিও আপনার পাশে আছি।",
                    "ধন্যবাদ—আমি চেষ্টা করব আরও ভালো সাহায্য করতে।",
                ),
                intent_key,
            ),
        }
        return m.get(intent_key, "বলুন, আমি শুনছি।")

    m_en = {
        "chitchat_thanks": _pick_variant(
            (
                "You're welcome—happy to help anytime.",
                "Any time! What else can I do for you?",
            ),
            intent_key,
        ),
        "chitchat_how_are_you": _pick_variant(
            (
                "I'm doing well, thanks—how about you? What should we tackle?",
                "All good on my side. What's on your mind?",
            ),
            intent_key,
        ),
        "chitchat_smalltalk": _pick_variant(
            (
                "I'm here—what would you like to do?",
                "Doing good. How can I help?",
            ),
            intent_key,
        ),
        "chitchat_greeting_time": _pick_variant(
            (
                "Hey there—I'm Jarvis. What can I do for you?",
                "Good to see you—how can I help today?",
            ),
            intent_key,
        ),
        "chitchat_listening_check": _pick_variant(
            (
                "Yes—I can hear you. Go ahead.",
                "I'm here and listening.",
                "Loud and clear. What's up?",
            ),
            intent_key,
        ),
        "chitchat_bye": _pick_variant(
            (
                "Take care—tap me anytime you need a hand.",
                "Catch you later!",
            ),
            intent_key,
        ),
        "chitchat_ack": _pick_variant(
            (
                "Okay—I'm ready when you are.",
                "Sure thing. What's next?",
            ),
            intent_key,
        ),
        "chitchat_warm": _pick_variant(
            (
                "That means a lot—I'm glad I'm useful.",
                "Thank you! I'll keep doing my best for you.",
            ),
            intent_key,
        ),
    }
    return m_en.get(intent_key, "I'm here—tell me what you need.")


def soft_unknown_reply(lang: str, seed: str) -> str:
    if lang == "bn":
        return _pick_variant(
            (
                "আমি পুরোটা বুঝতে পারিনি—ইউটিউব, গুগল, সময় বা আবহাওয়া বললে বুঝব।",
                "একটু অন্য ভাবে বলবে? যেমন ইউটিউবে কিছু সার্চ বা এখন সময় কত।",
            ),
            seed,
        )
    return _pick_variant(
        (
            "Hmm—I didn't quite catch that. Try something like opening YouTube, searching there, or asking the time.",
            "Could you rephrase? e.g. search on YouTube for… or what's the time?",
        ),
        seed,
    )


def localize_unknown(lang: str, raw: str) -> str:
    if lang == "bn":
        return "আমি পুরোটা বুঝতে পারিনি, আবার বলবে?"
    return "I couldn't quite understand that—could you say it again?"


def conversational_youtube_reply(action: str, user_text: str, lang: str) -> str:
    """Natural assistant-style line for UI + TTS (not a log string)."""
    from app.services.automation.youtube_multimodal import (
        parse_standalone_song_youtube,
        parse_youtube_multimodal,
    )

    qn = normalize_unicode(user_text)
    ql = qn.lower()
    spec = parse_youtube_multimodal(qn, ql)
    if spec is None and action == "system.youtube_play":
        spec = parse_standalone_song_youtube(ql, qn)
    kind = "open"
    query = ""
    if spec:
        kind = spec.kind
        query = (spec.query or "").strip()
    if action == "system.youtube_search":
        kind = "search"
    elif action == "system.youtube_play":
        kind = "play"
    elif action == "system.open_youtube":
        kind = "open"

    if kind == "open" and not query:
        if lang == "bn":
            return _pick_variant(
                (
                    "ঠিক আছে, আমি ইউটিউব খুলছি।",
                    "একটু অপেক্ষা করো, ইউটিউব খুলে দিচ্ছি।",
                ),
                user_text,
            )
        return _pick_variant(
            ("Sure—opening YouTube now.", "Got it—opening YouTube.", "On it—YouTube coming up."),
            user_text,
        )

    if not query:
        if lang == "bn":
            return "আচ্ছা, আমি এখন ইউটিউব খুলছি।"
        return "Opening YouTube for you."

    if lang == "bn":
        if kind == "play":
            return _pick_variant(
                (
                    f"ঠিক আছে, আমি গানটা চালানোর চেষ্টা করছি—ইউটিউবে ‘{query}’।",
                    f"একটু অপেক্ষা করো, ইউটিউবে ‘{query}’ চালাচ্ছি।",
                ),
                query,
            )
        return _pick_variant(
            (
                f"ঠিক আছে, ইউটিউবে {query} সার্চ করছি।",
                f"আমি এখনই ইউটিউব রেজাল্ট খুলছি—{query}।",
            ),
            query,
        )

    if kind == "play":
        return _pick_variant(
            (
                f"On it—I'm pulling up ‘{query}’ on YouTube for you.",
                f"Sure thing—searching YouTube for ‘{query}’ to play.",
            ),
            query,
        )
    return _pick_variant(
        (
            f"Alright—searching YouTube for {query}.",
            f"Got it—looking up {query} on YouTube.",
        ),
        query,
    )


def localize_action_result(
    action: str,
    raw: str,
    lang: str,
    intent: str,
    confidence: float,
    user_text: str = "",
) -> str:
    """Turn registry/tool output into user-visible text for the chosen language."""
    if lang != "bn":
        return raw

    if action == "system.unknown" or intent == "fallback":
        return localize_unknown(lang, raw)

    if action == "system.greet":
        return greeting_response(user_text, "bn")
    if action == "system.open_youtube":
        return "ইউটিউব খুলছি।"
    if action == "system.open_google":
        return _pick_variant(
            (
                "একটু অপেক্ষা করো, আমি গুগল খুলছি।",
                "ঠিক আছে, গুগল খুলছি।",
            ),
            raw,
        )
    if action == "system.time":
        return _pick_variant(
            (
                f"এখন সময় {format_time_bn()}।",
                f"ঠিক আছে—এখন সময় {format_time_bn()}।",
            ),
            raw,
        )
    if action in {"music.play", "music.play_random"}:
        return _pick_variant(
            (
                "ঠিক আছে, আমি গানটা চালানোর চেষ্টা করছি।",
                "চলছে—গান চালাচ্ছি, একটু অপেক্ষা করো।",
            ),
            raw,
        )
    if action == "weather.current":
        return f"আবহাওয়া বলছি—{raw}"
    if action == "ui.open_settings":
        return _pick_variant(
            (
                "ঠিক আছে, সেটিংস খুলছি।",
                "চলুন সেটিংসে যাই।",
            ),
            raw,
        )
    if action == "system.open_whatsapp":
        return _pick_variant(
            (
                "ঠিক আছে, হোয়াটসঅ্যাপ ওয়েব খুলছি।",
                "একটু অপেক্ষা করো, হোয়াটসঅ্যাপ খুলছি।",
            ),
            raw,
        )
    if action == "system.open_notepad":
        return _pick_variant(
            ("ঠিক আছে, নোটপ্যাড খুলছি।", "চলছে—নোটপ্যাড লাঞ্চ করছি।"),
            raw,
        )
    if action == "system.file_control":
        low = (raw or "").lower()
        if low.startswith("opened folder"):
            return "ঠিক আছে, আমি এখন ফোল্ডারটা খুলছি।"
        if low.startswith("opened file"):
            return "ঠিক আছে, আমি এখন ফাইলটা খুলছি।"
        if low.startswith("found "):
            return "আমি এখন ফাইলটা খুঁজছি। " + raw
        if "not found" in low or "could not find" in low:
            return "ফাইলটা খুঁজে পাইনি। আরেকটা নাম বলো।"
        return "একটু অপেক্ষা করো, কাজটা করছি।"
    if action == "system.battery":
        return f"ঠিক আছে—ব্যাটারি অবস্থা বলছি। {raw}"
    if action in {"whatsapp.send_stub", "whatsapp.send"} and "WhatsApp" in raw:
        return _pick_variant(
            (
                f"ঠিক আছে, হোয়াটসঅ্যাপে মেসেজ পাঠাচ্ছি। {raw}",
                f"আমি মেসেজ পাঠানোর চেষ্টা করছি। {raw}",
            ),
            raw,
        )
    if action.startswith("email."):
        if action == "email.send":
            return _pick_variant(
                (
                    "ঠিক আছে, ইমেইলটা পাঠিয়ে দিয়েছি।",
                    "আমি ইমেইল পাঠিয়ে দিয়েছি।",
                ),
                raw,
            )
        if action in {"email.flow_preview", "email.flow_confirm_needed"}:
            return _pick_variant(
                (
                    "আমি ড্রাফটটা বানিয়েছি। দেখে বলো, পাঠাবো কি?",
                    "ইমেইলটা রেডি। পাঠানোর আগে একবার কনফার্ম করো।",
                ),
                raw,
            )
        if action == "email.flow_cancel":
            return "ঠিক আছে, ইমেইল পাঠানো বন্ধ করলাম।"
        return "ঠিক আছে, ইমেইলের কাজ করছি।"

    return raw


def natural_english_reply(intent: str, action: str, raw: str, confidence: float, user_text: str) -> str:
    """Warmer English for common actions when not using robotic tool strings."""
    seed = user_text
    if action == "system.unknown" or intent == "fallback":
        if looks_conversational_soft(normalize_unicode(user_text), user_text.lower()):
            return soft_unknown_reply("en", user_text)
        return localize_unknown("en", raw)
    if action == "system.greet":
        return greeting_response(user_text, "en")
    if action == "system.time":
        return _pick_variant(
            (
                f"Sure—here's the time: {raw}",
                f"Got it. Right now it's {raw}",
            ),
            seed,
        )
    if action == "system.open_google":
        return _pick_variant(
            ("Opening Google for you.", "Sure—pulling up Google."),
            seed,
        )
    if action == "system.open_youtube":
        return _pick_variant(
            ("Sure—opening YouTube now.", "On it—YouTube's opening."),
            seed,
        )
    if action == "ui.open_settings":
        return _pick_variant(
            ("Okay—opening settings.", "Opening your settings tab."),
            seed,
        )
    if action in {"music.play", "music.play_random"}:
        return _pick_variant(
            ("Playing music for you.", "Starting playback—enjoy!"),
            seed,
        )
    if action == "system.open_whatsapp":
        return _pick_variant(
            ("Opening WhatsApp Web for you.", "One moment—launching WhatsApp."),
            seed,
        )
    if action == "system.file_control":
        return _pick_variant(
            ("On it—handling your file request now.", "Sure, I am working on that file task."),
            seed,
        )
    if action.startswith("email."):
        if action == "email.send":
            return _pick_variant(
                ("Done, I sent the email.", "Your email has been sent."),
                seed,
            )
        if action in {"email.flow_preview", "email.flow_confirm_needed"}:
            return _pick_variant(
                ("I prepared the draft. Please confirm before I send.", "Draft is ready. Confirm to send or edit it."),
                seed,
            )
        return _pick_variant(("Working on your email task.", "Handling your email request now."), seed)
    return raw


def stt_user_failure_message(lang: str, detail: str, stt_status: str) -> str:
    extra = f"{detail} ({stt_status})".strip()
    if lang == "bn":
        base = _pick_variant(
            (
                "হ্যাঁ, আমি শুনতে পাচ্ছি না পরিষ্কারভাবে—আরেকবার ধীরে বলবেন?",
                "একটু গোলমেলে শোনাল—আবার চেষ্টা করবেন?",
            ),
            extra,
        )
        return f"{base} ({extra}) মাইক আর ভাষা সেটিংস একবার দেখে নিন।"
    base = _pick_variant(
        (
            "I didn't quite catch that—could you say it again a little slower?",
            "Hmm, that came through fuzzy—mind repeating it?",
        ),
        extra,
    )
    return f"{base} ({extra}) Check your mic and speech language if you can."


def tts_unavailable_bangla_warning() -> str:
    return (
        "[TTS] এই সিস্টেমে বাংলা কণ্ঠস্বারের জন্য Windows ভয়েস ইনস্টল নাও থাকতে পারে। "
        "উত্তর টেক্সট দেখানো হচ্ছে; ভয়েস ট্যাবে উপযুক্ত ভয়েস বেছে নিন।"
    )


def tts_speak_failed_message(lang: str) -> str:
    if lang == "bn":
        return "[TTS] কথা বলার সময় ড্রাইভার ত্রুটি। টেক্সট উত্তর এখনও পাওয়া যাচ্ছে।"
    return "[TTS] Speech output failed (audio driver). Text response is still shown."


def whatsapp_flow_ask_recipient(lang_v: str) -> str:
    if lang_v == "bn":
        return _pick_variant(
            (
                "কার কাছে পাঠাবো?",
                "কাকে মেসেজ পাঠাবো?",
            ),
            "wa_to",
        )
    return _pick_variant(
        ("Who should I send this to?", "Which contact? Give a name or +country code number."),
        "wa_to",
    )


def whatsapp_flow_ask_message(lang_v: str) -> str:
    if lang_v == "bn":
        return _pick_variant(
            ("কি লিখবো?", "মেসেজটা কী হবে?"),
            "wa_msg",
        )
    return "What should the message say?"


def whatsapp_flow_no_contact(lang_v: str) -> str:
    if lang_v == "bn":
        return (
            "এই নামে কন্টাক্ট সেভ করা নেই। আন্তর্জাতিক ফরম্যাটে নম্বর বলো—যেমন +৮৮০১৭১১২৩৪৫৬৭। "
            "(সেটিংসের `whatsapp_contacts_json` কীতে নাম→নম্বর ম্যাপ যোগ করতে পারো।)"
        )
    return (
        "I don't have that name saved. Say the phone number with country code, e.g. +880171112345678. "
        "You can add aliases in settings key whatsapp_contacts_json."
    )


def whatsapp_flow_cancelled(lang_v: str) -> str:
    if lang_v == "bn":
        return "ঠিক আছে, হোয়াটসঅ্যাপ মেসেজ বন্ধ করলাম।"
    return "Okay—I cancelled the WhatsApp message."


def whatsapp_flow_sending(lang_v: str) -> str:
    if lang_v == "bn":
        return "ঠিক আছে, আমি মেসেজ পাঠাচ্ছি।"
    return "Alright—sending the message now."
