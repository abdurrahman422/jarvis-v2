from __future__ import annotations

import re

from app.core.fuzzy_intent_matcher import match_fuzzy_intent
from app.core.locale_responses import classify_conversational_message, normalize_unicode
from app.actions.file_actions import looks_like_desktop_launch
from app.services.automation.youtube_multimodal import (
    mentions_youtube,
    parse_standalone_song_youtube,
    parse_youtube_multimodal,
)


_BN_OPEN_HINTS: tuple[str, ...] = (
    "খুল",
    "ওপেন",
    "করো",
    "করুন",
    "করে",
    "চালু",
    "দেখা",
    "দেখাই",
    "দেখি",
    "দেখতে",
    "দাও",
    "দিন",
    "যাও",
    "যান",
    "স্টার্ট",
    "খোল",
    "লাঞ্চ",
    "চালাও",
    "চালান",
    "চাই",
)

_BN_TIME_PHRASES: tuple[str, ...] = (
    "কয়টা বাজে",
    "কয়টা বাজে",
    "কটা বাজে",
    "এখন কয়টা",
    "এখন কয়টা",
    "কি সময়",
    "কি সময়",
    "সময় বলো",
    "সময় বলো",
    "সময় কত",
    "সময় কত",
    "সময়টা",
    "সময়টা",
    "টাইম বলো",
    "সময় বলুন",
    "সময় বলুন",
    "সময় হয়েছে",
    "সময় হয়েছে",
    "ঘড়িতে",
    "ঘড়িতে",
    "বাজে কয়টা",
    "বাজে কয়টা",
    "এখন সময়",
    "এখন সময়",
)


class IntentResult:
    def __init__(
        self,
        intent: str,
        action: str,
        confidence: float,
        needs_confirmation: bool = False,
    ) -> None:
        self.intent = intent
        self.action = action
        self.confidence = confidence
        self.needs_confirmation = needs_confirmation


def _bangla_implies_open_or_launch(q: str, ql: str) -> bool:
    return any(hint in q for hint in _BN_OPEN_HINTS) or any(
        hint in ql for hint in ("kholo", "open", "launch", "start", "chalao")
    )


class IntentRouter:
    def route(self, text: str) -> IntentResult:
        q = normalize_unicode(text)
        ql = q.lower()

        if not q:
            return IntentResult("unknown", "system.unknown", 0.2)

        if self._open_youtube_direct(q, ql):
            return IntentResult("open_web", "system.open_youtube", 0.94)

        yt = parse_youtube_multimodal(q, ql)
        if yt is not None:
            if yt.kind == "play":
                return IntentResult("youtube_play", "system.youtube_play", 0.93)
            if yt.kind == "search":
                return IntentResult("youtube_search", "system.youtube_search", 0.91)
            return IntentResult("open_web", "system.open_youtube", 0.9)

        song = parse_standalone_song_youtube(ql, q)
        if song is not None:
            return IntentResult("youtube_play", "system.youtube_play", 0.9)

        if self._whatsapp_send_file_flow(q, ql):
            return IntentResult("whatsapp_send_file_flow", "whatsapp.send_file_flow", 0.88)
        if self._whatsapp_send_flow(q, ql):
            return IntentResult("whatsapp_send_flow", "whatsapp.flow_start", 0.88)
        if self._whatsapp_open(q, ql):
            return IntentResult("whatsapp_open", "system.open_whatsapp", 0.9)

        if self._file_control_intent(q, ql):
            return IntentResult("file_control", "system.file_control", 0.86)

        if self._bangla_open_google(q, ql) or "open google" in ql or ql.strip() in {"google", "google kholo"}:
            return IntentResult("open_web", "system.open_google", 0.9)

        if mentions_youtube(q, ql):
            return IntentResult("open_web", "system.open_youtube", 0.9)

        if self._bangla_open_settings_inapp(q, ql):
            return IntentResult("open_settings", "system.status", 0.82)

        if self._bangla_play_music(q, ql):
            return IntentResult("music_control", "music.play", 0.86)

        if self._bangla_weather(q, ql) or any(word in ql for word in ("weather", "forecast", "temperature")):
            return IntentResult("weather_query", "weather.current", 0.84)

        if self._bangla_time(q, ql) or re.search(r"\b(time|clock|what time)\b", ql):
            return IntentResult("time_query", "system.time", 0.9)

        if any(word in ql for word in ("battery", "charge", "power level")):
            return IntentResult("battery_query", "system.battery", 0.88)

        if any(word in ql for word in ("status", "system info", "pc info", "computer info")):
            return IntentResult("system_status", "system.status", 0.82)

        if any(word in ql for word in ("speed test", "speedtest", "internet speed")):
            return IntentResult("network_speed", "network.speedtest", 0.86)

        if "notepad" in ql and any(word in ql for word in ("open", "launch", "start")):
            return IntentResult("open_app", "system.open_notepad", 0.88)

        if looks_like_desktop_launch(q, ql):
            return IntentResult("desktop_open", "system.open_desktop_item", 0.82)

        if any(word in ql for word in ("play music", "music play", "start music")):
            return IntentResult("music_control", "music.play", 0.86)
        if any(word in ql for word in ("random music", "shuffle music")):
            return IntentResult("music_control", "music.play_random", 0.84)
        if any(word in ql for word in ("next song", "next track")):
            return IntentResult("music_control", "music.next", 0.84)
        if any(word in ql for word in ("previous song", "previous track", "back song")):
            return IntentResult("music_control", "music.previous", 0.84)
        if any(word in ql for word in ("stop music", "pause music")):
            return IntentResult("music_control", "music.stop", 0.84)

        if any(word in ql for word in ("hello", "hi", "hey", "assalam", "salam")) or any(
            word in q for word in ("হ্যালো", "সালাম", "আসসালামু")
        ):
            return IntentResult("greeting", "system.greet", 0.95)

        chitchat = classify_conversational_message(q, ql)
        if chitchat:
            return IntentResult(chitchat, "system.chitchat", 0.86)

        fuzzy = match_fuzzy_intent(q)
        if fuzzy is not None:
            return IntentResult(
                fuzzy.intent,
                fuzzy.action,
                fuzzy.confidence,
                fuzzy.needs_confirmation,
            )

        return IntentResult("unknown", "system.unknown", 0.35)

    def _bangla_open_google(self, q: str, ql: str) -> bool:
        return ("গুগল" in q or "google" in ql) and _bangla_implies_open_or_launch(q, ql)

    def _open_youtube_direct(self, q: str, ql: str) -> bool:
        direct = {
            "open youtube",
            "youtube kholo",
            "youtube khulo",
            "youtube open",
            "ওপেন ইউটিউব",
            "ইউটিউব খোলো",
            "ইউটিউব খুলো",
            "ইউটিউব খুলো",
        }
        return ql.strip() in direct or q.strip() in direct

    def _bangla_time(self, q: str, ql: str) -> bool:
        return any(phrase in q for phrase in _BN_TIME_PHRASES) or "time bolo" in ql

    def _file_control_intent(self, q: str, ql: str) -> bool:
        file_words = (
            "file",
            "folder",
            "download",
            "downloads",
            "desktop",
            "document",
            "documents",
            "latest",
            "last file",
            "ফাইল",
            "ফোল্ডার",
            "ডাউনলোড",
            "ডেস্কটপ",
        )
        actions = ("open", "find", "search", "show", "খুল", "খুঁজ", "দেখ")
        return any(word in ql or word in q for word in file_words) and any(
            action in ql or action in q for action in actions
        )

    def _email_flow_intent(self, q: str, ql: str) -> bool:
        return "email" in ql or "ইমেইল" in q or "মেইল" in q

    def _bangla_play_music(self, q: str, ql: str) -> bool:
        return ("গান" in q or "music" in ql) and any(
            word in q or word in ql for word in ("চালাও", "চালান", "play", "chalao")
        )

    def _bangla_open_settings_inapp(self, q: str, ql: str) -> bool:
        return ("settings" in ql or "সেটিং" in q) and _bangla_implies_open_or_launch(q, ql)

    def _bangla_weather(self, q: str, ql: str) -> bool:
        return any(word in q for word in ("আবহাওয়া", "আবহাওয়া", "তাপমাত্রা")) or "weather" in ql

    def _whatsapp_open(self, q: str, ql: str) -> bool:
        return ("whatsapp" in ql or "হোয়াটসঅ্যাপ" in q or "হোয়াটসঅ্যাপ" in q) and not self._whatsapp_send_flow(q, ql)

    def _whatsapp_send_flow(self, q: str, ql: str) -> bool:
        if "whatsapp" not in ql and "হোয়াটসঅ্যাপ" not in q and "হোয়াটসঅ্যাপ" not in q:
            return False
        return any(word in ql for word in ("send", "message", "text")) or any(
            word in q for word in ("পাঠাও", "মেসেজ", "বার্তা")
        )

    def _whatsapp_send_file_flow(self, q: str, ql: str) -> bool:
        if not self._whatsapp_send_flow(q, ql):
            return False
        return any(word in ql for word in ("file", "photo", "image", "document")) or any(
            word in q for word in ("ফাইল", "ছবি", "ডকুমেন্ট")
        )
