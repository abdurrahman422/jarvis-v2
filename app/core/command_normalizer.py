from __future__ import annotations

import logging
import re

LOG = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[।,;:!?()\[\]{}\"']")
_SPACE_RE = re.compile(r"\s+")

APP_ALIASES: dict[str, list[str]] = {
    "youtube": ["youtube", "ইউটিউব"],
    "chrome": ["chrome", "google chrome", "chrome browser", "ক্রোম", "ক্রোম ব্রাউজার"],
    "notepad": ["notepad", "নোটপ্যাড", "নোট প্যাড"],
    "calculator": ["calculator", "calc", "ক্যালকুলেটর", "ক্যালকুলেটার"],
    "paint": ["paint", "mspaint", "পেইন্ট"],
    "vscode": ["vscode", "vs code", "visual studio code", "ভিএস কোড", "ভি এস কোড"],
    "whatsapp": ["whatsapp", "whats app", "হোয়াটসঅ্যাপ", "হোয়াটসঅ্যাপ", "হোয়াটস অ্যাপ", "হোয়াটস অ্যাপ"],
    "chatgpt": ["chatgpt", "চ্যাটজিপিটি", "এসজিপিটি", "সিজিপিটি"],
    "edge": ["edge", "microsoft edge", "ms edge"],
    "firefox": ["firefox", "mozilla firefox"],
    "brave": ["brave", "brave browser"],
    "facebook": ["facebook", "ফেসবুক"],
    "messenger": ["messenger", "মেসেঞ্জার"],
    "word": ["word", "microsoft word", "ওয়ার্ড", "ওয়ার্ড"],
    "excel": ["excel", "microsoft excel", "এক্সেল"],
    "powerpoint": ["powerpoint", "power point", "ppt", "পাওয়ারপয়েন্ট", "পাওয়ারপয়েন্ট"],
    "file explorer": ["file explorer", "explorer", "files", "ফাইল এক্সপ্লোরার", "এক্সপ্লোরার"],
    "control panel": ["control panel", "কন্ট্রোল প্যানেল"],
    "settings": ["settings", "সেটিংস"],
    "camera": ["camera", "ক্যামেরা"],
    "spotify": ["spotify", "স্পটিফাই"],
    "vlc": ["vlc", "vlc player"],
    "telegram": ["telegram", "টেলিগ্রাম"],
    "zoom": ["zoom"],
    "discord": ["discord"],
    "github desktop": ["github desktop", "github"],
    "cmd": ["cmd", "command prompt"],
    "powershell": ["powershell", "power shell"],
    "windows terminal": ["windows terminal", "terminal"],
    "task manager": ["task manager", "taskmgr", "টাস্ক ম্যানেজার"],
    "cursor": ["cursor"],
    "pycharm": ["pycharm"],
}

_PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("google chrome", " chrome "),
    ("chrome browser", " chrome "),
    ("ক্রোম ব্রাউজার", " chrome "),
    ("visual studio code", " vscode "),
    ("vs code", " vscode "),
    ("v s code", " vscode "),
    ("ভিএস কোড", " vscode "),
    ("ভি এস কোড", " vscode "),
    ("whats app", " whatsapp "),
    ("হোয়াটস অ্যাপ", " whatsapp "),
    ("হোয়াটস অ্যাপ", " whatsapp "),
    ("হোয়াটসঅ্যাপ", " whatsapp "),
    ("হোয়াটসঅ্যাপ", " whatsapp "),
    ("চ্যাটজিপিটি", " chatgpt "),
    ("এসজিপিটি", " chatgpt "),
    ("সিজিপিটি", " chatgpt "),
    ("ইউটিউব", " youtube "),
    ("ক্রোম", " chrome "),
    ("নোটপ্যাড", " notepad "),
    ("নোট প্যাড", " notepad "),
    ("ক্যালকুলেটর", " calculator "),
    ("ক্যালকুলেটার", " calculator "),
    ("গুগলে", " google "),
    ("গুগল", " google "),
    ("ওয়েবে", " web "),
    ("ওয়েবে", " web "),
    ("সার্চ", " search "),
    ("খুঁজো", " search "),
    ("খুজো", " search "),
    ("খুঁজুন", " search "),
    ("খুজুন", " search "),
    ("ওপেন", " open "),
    ("খুলো", " open "),
    ("খুলুন", " open "),
    ("চালু", " open "),
    ("চালাও", " open "),
    ("লঞ্চ", " open "),
)

_FILLER_PHRASES: tuple[str, ...] = (
    "আমার জন্য",
    "দয়া করে",
    "দয়া করে",
    "করে দাও",
    "খুলে দাও",
    "for me",
)

_FILLER_WORDS = {
    "sir",
    "please",
    "pls",
    "jarvis",
    "for",
    "me",
    "app",
    "software",
    "browser",
    "open",
    "launch",
    "start",
    "run",
    "জার্ভিস",
    "জারভিস",
    "স্যার",
    "ভাই",
    "প্লিজ",
    "দয়া",
    "দয়া",
    "করে",
    "করো",
    "করুন",
    "দাও",
    "আমাকে",
    "আমার",
    "জন্য",
    "তুমি",
    "খুলে",
    "খুলো",
    "চালু",
    "চালাও",
    "ব্রাউজার",
    "অ্যাপ",
    "সফটওয়্যার",
    "সফটওয়্যার",
}

_OPEN_WORDS = {"open", "launch", "start", "run", "kholo", "khulo", "chalao"}
_SEARCH_WORDS = {"search", "find", "look", "খুঁজে", "খুজে", "খুঁজো", "খুজো"}
_SEARCH_DROP_WORDS = {
    "google",
    "web",
    "search",
    "on",
    "for",
    "এ",
    "তে",
    "সার্চ",
    "খুঁজো",
    "খুজো",
    "দাও",
    "করো",
    "করুন",
    "বলো",
    "বলুন",
    "bolo",
    "tell",
    "me",
}


def normalize_voice_command(text: str, *, log: bool = True) -> str:
    if log:
        LOG.info("[command] original: %s", text)
    value = f" {text or ''} ".lower()
    for src in _FILLER_PHRASES:
        value = value.replace(src, " ")
    for src, dst in _PHRASE_REPLACEMENTS:
        value = value.replace(src, dst)
    value = _PUNCT_RE.sub(" ", value)
    words = [word for word in _SPACE_RE.split(value) if word and word not in _FILLER_WORDS]
    normalized = " ".join(words).strip()
    if log:
        LOG.info("[command] normalized: %s", normalized)
    return normalized


def resolve_app_name(text: str) -> str:
    haystack = f" {normalize_voice_command(text, log=False)} "
    raw = f" {(text or '').lower()} "
    best: tuple[int, str] | None = None
    for canonical, aliases in APP_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_voice_command(alias, log=False)
            candidates = [alias_norm, alias.lower()]
            for candidate in candidates:
                candidate = candidate.strip()
                if not candidate:
                    continue
                needle = f" {candidate} "
                if needle in haystack or needle in raw:
                    score = len(candidate)
                    if best is None or score > best[0]:
                        best = (score, canonical)
    resolved = best[1] if best else ""
    LOG.info("[command] resolved_app: %s", resolved)
    return resolved


def is_google_search_command(normalized: str) -> bool:
    tokens = set((normalized or "").split())
    return "search" in tokens and ("google" in tokens or "web" in tokens or len(tokens - _SEARCH_WORDS) > 0)


def extract_google_search_query(original: str, normalized: str) -> str:
    query = normalized or normalize_voice_command(original)
    query = re.sub(r"\b(search on google|google search|search google)\b", " ", query)
    words = [word for word in _SPACE_RE.split(query) if word and word not in _SEARCH_DROP_WORDS]
    cleaned = _SPACE_RE.sub(" ", " ".join(words)).strip()
    return cleaned or (original or "").strip()


def is_open_app_command(normalized: str, original: str = "") -> bool:
    if "search" in set((normalized or "").split()):
        return False
    if resolve_app_name(f"{original} {normalized}"):
        return True
    return bool(set((normalized or "").split()) & _OPEN_WORDS)


def extract_app_name(normalized: str) -> str:
    words = [
        word
        for word in (normalized or "").split()
        if word not in _OPEN_WORDS and word not in _FILLER_WORDS
    ]
    return " ".join(words).strip()
