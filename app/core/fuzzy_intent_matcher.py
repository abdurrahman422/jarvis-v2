from dataclasses import dataclass
from difflib import SequenceMatcher


try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - depends on optional local install
    fuzz = None


@dataclass(frozen=True)
class FuzzyIntentMatch:
    intent: str
    action: str
    confidence: float
    phrase: str
    needs_confirmation: bool


_DANGEROUS_WORDS = ("delete", "remove", "shutdown", "restart", "format", "wipe")
_QUESTION_STARTERS = (
    "what is",
    "what's",
    "who is",
    "why",
    "how do",
    "how to",
    "can you",
    "could you",
    "would you",
    "tell me",
    "explain",
)

_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("open_web", "system.open_youtube", "open youtube"),
    ("open_web", "system.open_youtube", "youtube open"),
    ("open_web", "system.open_youtube", "youtube kholo"),
    ("open_web", "system.open_youtube", "youtub kholo"),
    ("open_web", "system.open_google", "open google"),
    ("open_web", "system.open_google", "google kholo"),
    ("desktop_open", "system.open_desktop_item", "open chrome"),
    ("desktop_open", "system.open_desktop_item", "chrome open"),
    ("desktop_open", "system.open_desktop_item", "chrome open koro"),
    ("desktop_open", "system.open_desktop_item", "chrom open koro"),
    ("desktop_open", "system.open_desktop_item", "open notepad"),
    ("whatsapp_open", "system.open_whatsapp", "open whatsapp"),
    ("whatsapp_open", "system.open_whatsapp", "whatsapp kholo"),
    ("voice_control", "voice.volume_up", "volume up"),
    ("voice_control", "voice.volume_up", "increase volume"),
    ("voice_control", "voice.volume_up", "volum barao"),
    ("voice_control", "voice.volume_up", "volume barao"),
    ("voice_control", "voice.volume_down", "volume down"),
    ("voice_control", "voice.volume_down", "decrease volume"),
    ("voice_control", "voice.volume_down", "volume komao"),
    ("voice_control", "voice.rate_up", "speak faster"),
    ("voice_control", "voice.rate_down", "speak slower"),
    ("music_control", "music.play", "play music"),
    ("music_control", "music.play", "music chalao"),
    ("music_control", "music.stop", "stop music"),
    ("music_control", "music.next", "next song"),
    ("music_control", "music.previous", "previous song"),
    ("time_query", "system.time", "what time is it"),
    ("time_query", "system.time", "time bolo"),
    ("battery_query", "system.battery", "battery status"),
    ("weather_query", "weather.current", "weather"),
    ("network_speed", "network.speedtest", "speed test"),
    ("alarm_delete", "scheduler.alarm_remove", "delete alarm"),
    ("alarm_delete", "scheduler.alarm_remove", "remove alarm"),
)


def _clean(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _score(query: str, phrase: str) -> float:
    if fuzz is not None:
        return fuzz.WRatio(query, phrase) / 100.0
    return SequenceMatcher(None, query, phrase).ratio()


def _requires_confirmation(action: str, confidence: float, query: str) -> bool:
    if confidence < 0.85:
        return True
    return any(word in query for word in _DANGEROUS_WORDS) or any(word in action for word in ("delete", "remove", "shutdown"))


def match_fuzzy_intent(text: str) -> FuzzyIntentMatch | None:
    query = _clean(text)
    if not query:
        return None
    if query.endswith("?") or query.startswith(_QUESTION_STARTERS):
        return None

    best: tuple[str, str, str, float] | None = None
    for intent, action, phrase in _CANDIDATES:
        score = _score(query, phrase)
        if best is None or score > best[3]:
            best = (intent, action, phrase, score)

    if best is None or best[3] < 0.60:
        return None

    intent, action, phrase, confidence = best
    return FuzzyIntentMatch(
        intent=f"fuzzy_{intent}",
        action=action,
        confidence=round(confidence, 2),
        phrase=phrase,
        needs_confirmation=_requires_confirmation(action, confidence, query),
    )
