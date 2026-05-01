from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote_plus

from app.core.command_normalizer import (
    extract_google_search_query,
    is_google_search_command,
    normalize_voice_command,
)
from app.core.locale_responses import normalize_unicode
from app.services.web.web_search_service import SearchResponse, search_web

WEATHER_KEYWORDS = (
    "আবহাওয়া",
    "আবহাওয়া",
    "আবহাওয়ার",
    "আবহাওয়ার",
    "আবহাওয়ার খবর",
    "আবহাওয়ার খবর",
    "ওয়েদার",
    "ওয়েদার",
    "weather",
    "তাপমাত্রা",
    "বৃষ্টি",
)


@dataclass
class WebActionResult:
    intent: str
    action: str
    query: str
    response: str
    confidence: float
    success: bool
    search_kind: str
    search_url: str
    google_url: str
    results: list[dict] = field(default_factory=list)
    error: str = ""
    speak_text: str = ""


def is_web_or_weather_query(text: str, normalized_text: str = "", mode: str = "chat") -> bool:
    normalized = normalized_text or normalize_voice_command(text, log=False)
    if is_weather_query(text, normalized):
        return True
    if is_google_search_command(normalized):
        return True
    tokens = set((normalized or "").split())
    lowered = normalize_unicode(text).strip().lower()
    if _contains_any(lowered, ("সার্চ", "খুঁজো", "খুঁজে দাও", "গুগল", "গুগলে", "ওয়েবে", "ওয়েবে", "খবর কি")):
        return True
    if {"weather", "আবহাওয়া", "আবহাওয়া", "ওয়েদার", "ওয়েদার"} & tokens:
        return True
    question_prefixes = (
        "who ",
        "what ",
        "when ",
        "where ",
        "why ",
        "how ",
        "কে ",
        "কী ",
        "কি ",
        "কখন ",
        "কোথায় ",
        "কোথায় ",
        "কেন ",
        "কিভাবে ",
    )
    question_markers = (" কে", " কী", " কি", " কবে", " কোথায়", " কোথায়", " কত")
    return mode == "voice" and (
        lowered.endswith("?")
        or lowered.startswith(question_prefixes)
        or any(marker in lowered for marker in question_markers)
    )


def handle_web_or_weather_query(text: str, *, weather_search: bool = False) -> SearchResponse:
    query = build_web_search_query(text, weather_search=weather_search)
    return search_web(query)


def execute_web_route(text: str, normalized_text: str = "", mode: str = "chat") -> WebActionResult | None:
    normalized = normalized_text or normalize_voice_command(text, log=False)
    weather_search = is_weather_query(text, normalized)
    if not is_web_or_weather_query(text, normalized, mode):
        return None
    query = build_web_search_query(text, normalized_text=normalized, weather_search=weather_search)
    if not query:
        return None
    result = search_web(query)
    summary = result.summary
    if weather_search and result.error:
        summary = "স্যার, ইন্টারনেট কানেকশন সমস্যা হচ্ছে, তাই আবহাওয়ার তথ্য আনতে পারিনি।"
    return WebActionResult(
        intent="weather_search" if weather_search else "google_search",
        action="web.search",
        query=query,
        response=summary,
        confidence=0.95 if result.results else 0.45,
        success=not bool(result.error),
        search_kind="weather" if weather_search else "web",
        search_url=result.search_url,
        google_url=result.search_url,
        results=[
            {"title": item.title, "snippet": item.snippet, "url": item.url}
            for item in result.results
        ],
        error=result.error,
        speak_text=summary,
    )


def build_web_search_query(text: str, normalized_text: str = "", *, weather_search: bool = False) -> str:
    normalized = normalized_text or normalize_voice_command(text, log=False)
    if weather_search:
        lowered = (text or "").strip().lower()
        if _contains_any(lowered, ("kaliganj", "কালীগঞ্জ", "bangladesh", "বাংলাদেশ", "dhaka", "ঢাকা")):
            return extract_google_search_query(text, normalized).strip()
        if any(ord(ch) > 127 for ch in text):
            return "আজকের আবহাওয়া Kaliganj Bangladesh"
        return "today weather Kaliganj Bangladesh"
    return extract_google_search_query(text, normalized)


def google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def matches_weather_keywords(text: str, normalized_text: str = "") -> bool:
    value = f"{text or ''} {normalized_text or ''}".casefold()
    value = value.replace("য়", "য়")
    return any(keyword.casefold() in value or keyword.casefold().replace("য়", "য়") in value for keyword in WEATHER_KEYWORDS)


def is_weather_query(text: str, normalized_text: str = "") -> bool:
    if matches_weather_keywords(text, normalized_text):
        return True
    value = f"{normalize_unicode(text).strip().lower()} {(normalized_text or '').lower()}"
    return _contains_any(
        value,
        (
            "আবহাওয়া",
            "আবহাওয়া",
            "আবহাওয়ার খবর",
            "আবহাওয়ার খবর",
            "আবহাওয়া কেমন",
            "ওয়েদার",
            "ওয়েদার",
            "weather",
            "today weather",
            "তাপমাত্রা",
            "বৃষ্টি",
            "আজকে বৃষ্টি হবে",
        ),
    )


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    folded = (value or "").casefold()
    return any(needle.casefold() in folded for needle in needles)
