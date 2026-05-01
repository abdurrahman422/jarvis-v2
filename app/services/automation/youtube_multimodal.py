"""
Multi-intent YouTube commands: platform + action (open/search/play) + query.
Supports Bangla, English, Banglish, and mixed phrasing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional
import unicodedata

from app.services.offline_guard import block_internet

Kind = Literal["open", "search", "play"]


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", (text or "").strip())


@dataclass(frozen=True)
class YouTubeIntent:
    kind: Kind
    query: Optional[str]


_REGEX_OPEN_AND_SEARCH_EN = re.compile(
    r"open\s+youtube\s+(?:and\s+)?(?:search|find)\s+(.+)",
    re.IGNORECASE,
)
_REGEX_YT_E_SEARCH = re.compile(
    r"youtube\s+e\s+(.+?)\s+search\b",
    re.IGNORECASE,
)
_REGEX_SEARCH_ON_YT = re.compile(
    r"(?:search|find)\s+(.+?)\s+(?:on\s+)?youtube",
    re.IGNORECASE,
)
_REGEX_YT_SEARCH = re.compile(r"youtube\s+search\s+(.+)", re.IGNORECASE)
_REGEX_BN_YT_QUERY_SEARCH = re.compile(r"ইউটিউবে\s+(.+?)\s+(?:সার্চ|খুঁজে?)\s*(?:দাও|দিন|করো|কর)?")
_REGEX_BN_SEARCH_YT = re.compile(r"(?:সার্চ|খুঁজো?|খুঁজ)\s+(.+?)\s+ইউটিউব(?:ে)?")
_REGEX_BN_NEWS_SEARCH = re.compile(
    r"ইউটিউবে\s*(?:খবর|নিউজ)?\s*(?:সার্চ|খুঁজ)?\s*(?:দাও|দিন|করো)?\s*(?:খবর|নিউজ)?"
)
_REGEX_EN_YOUTUBE_PLAY_SONG = re.compile(
    r"youtube\s+play\s+(?:song\s+)?(.+)",
    re.IGNORECASE,
)

_FILLER_TOKENS = frozenset(
    {
        "youtube",
        "youtu.be",
        "yt",
        "open",
        "and",
        "the",
        "a",
        "an",
        "on",
        "in",
        "for",
        "to",
        "e",
        "dao",
        "daw",
        "koro",
        "kor",
        "kholo",
        "khul",
        "please",
        "search",
        "find",
        "play",
        "song",
        "video",
        "টা",
        "এই",
        "ও",
        "এ",
    }
)


def mentions_youtube(q: str, ql: str) -> bool:
    if "ইউটিউব" in q or "ইউ টিউব" in q:
        return True
    if "youtube" in ql or "youtu.be" in ql:
        return True
    return bool(re.search(r"\byt\b", ql))


def _has_search_intent(q: str, ql: str) -> bool:
    if any(m in ql for m in ("search", "find", "lookup")):
        return True
    if any(m in q for m in ("সার্চ", "খুঁজ", "খুঁজে", "খুঁজি", "খুঁজো")):
        return True
    if "খবর" in q and ("সার্চ" in q or "খুঁজ" in q or "দাও" in q or "ইউটিউব" in q):
        return True
    if "নিউজ" in q and ("ইউটিউব" in q or "সার্চ" in q):
        return True
    if "actor" in ql and ("youtube" in ql or "search" in ql):
        return True
    if "search" in ql and any(m in ql for m in ("dao", "daw", "koro", "korun", "koren")):
        return True
    return False


def _has_play_intent(q: str, ql: str) -> bool:
    if re.search(r"\byoutube\s+search\b", ql) or ("youtube" in ql and " search " in f" {ql} "):
        return False
    if "youtube play" in ql or re.search(r"\bplay\s+.+\s+youtube\b", ql):
        return True
    if re.search(r"\bplay\s+", ql) and "youtube" in ql and "search" not in ql:
        return True
    if any(m in ql for m in ("stream",)):
        return True
    if any(m in q for m in ("চালাও", "চালান", "চালাই", "বাজাও", "ভিডিও", "শুন")):
        return True
    if "গান" in q and ("চাল" in q or "বাজ" in q or "ইউটিউব" in q):
        return True
    if re.search(r"\bgan\b", ql) and ("chalao" in ql or "play" in ql or "koro" in ql):
        return True
    if "song" in ql and "youtube" in ql and "search" not in ql:
        return True
    return False


def _regex_query(q: str, ql: str) -> Optional[str]:
    m = _REGEX_OPEN_AND_SEARCH_EN.search(ql)
    if m:
        return m.group(1).strip(" ,.!?।")
    m = _REGEX_YT_SEARCH.match(ql)
    if m:
        return m.group(1).strip(" ,.!?।")
    m = _REGEX_EN_YOUTUBE_PLAY_SONG.match(ql)
    if m:
        tail = m.group(1).strip(" ,.!?।")
        if tail:
            return tail
    m = _REGEX_YT_E_SEARCH.match(ql)
    if m:
        return m.group(1).strip(" ,.!?।")
    m = _REGEX_SEARCH_ON_YT.match(ql)
    if m:
        return m.group(1).strip(" ,.!?।")
    m = _REGEX_BN_YT_QUERY_SEARCH.search(q)
    if m:
        inner = m.group(1).strip(" ,.!?।")
        inner = re.sub(r"^(খবর|নিউজ|গান)\s+", "", inner).strip()
        return inner
    m = _REGEX_BN_SEARCH_YT.search(q)
    if m:
        return m.group(1).strip(" ,.!?।")
    if _REGEX_BN_NEWS_SEARCH.search(q) and "খবর" in q:
        return "খবর"
    if "ইউটিউব" in q and "খবর" in q and _has_search_intent(q, ql):
        return "খবর"
    if "youtube" in ql and "news" in ql:
        return "news"
    if "youtube" in ql and "actor" in ql:
        m2 = re.search(r"actor\s+(.+)", ql, re.IGNORECASE)
        if m2:
            return m2.group(1).strip(" ,.!?।")
        return "actor"
    return None


def _strip_youtube_markers(text: str, ql: str) -> str:
    work = text
    for pat in (
        r"ইউটিউবে?",
        r"ইউ\s*টিউব",
        r"youtube",
        r"youtu\.be",
        r"\byt\b",
    ):
        work = re.sub(pat, " ", work, flags=re.IGNORECASE)
    return _norm(re.sub(r"\s+", " ", work))


def _strip_filler_words(fragment: str, ql_frag: str) -> str:
    toks = []
    for t in fragment.split():
        tl = re.sub(r"^[^\w\u0980-\u09FF]+|[^\w\u0980-\u09FF]+$", "", t.lower())
        if tl in _FILLER_TOKENS:
            continue
        if tl in {"somoy", "shomoy", "tv"}:
            toks.append(t)
            continue
        if len(tl) <= 1 and tl.isascii():
            continue
        toks.append(t)
    out = " ".join(toks).strip()
    return out if out else fragment.strip()


def extract_youtube_query(q: str, ql: str, kind: Kind) -> str:
    rq = _regex_query(q, ql)
    if rq is not None:
        stripped = _strip_filler_words(rq, rq.lower())
        if stripped or rq == "":
            return stripped or rq

    work = _strip_youtube_markers(q, ql)

    for pat in (
        r"\bsearch\b",
        r"\bfind\b",
        r"সার্চ",
        r"খুঁজে?",
        r"খুঁজি",
        r"\bplay\b",
        r"চালাও|চালান|চালাই",
        r"বাজাও",
        r"\bgan\b",
        r"গান",
        r"ভিডিও",
        r"\bvideo\b",
        r"\bsong\b",
        r"দাও|দিন|করো|করুন|করি",
        r"খুল|খোল|open",
    ):
        work = re.sub(pat, " ", work, flags=re.IGNORECASE)
    work = _norm(re.sub(r"\s+", " ", work))
    work = _strip_filler_words(work, work.lower())

    if kind == "play" and work.startswith("টা "):
        work = work[2:].strip()
    return work.strip(" ,.!?।-")


def parse_youtube_multimodal(q: str, ql: str) -> Optional[YouTubeIntent]:
    if not mentions_youtube(q, ql):
        return None

    kind: Kind = "open"
    if _has_search_intent(q, ql):
        kind = "search"
    elif _has_play_intent(q, ql):
        kind = "play"
    elif " and " in ql or " এবং " in q or " আর " in q:
        if "search" in ql or "খুঁজ" in q or "সার্চ" in q:
            kind = "search"

    query = extract_youtube_query(q, ql, kind)
    if (not query) and kind == "open":
        stripped = _strip_youtube_markers(q, ql)
        tail = _strip_filler_words(stripped, stripped.lower())
        if tail and len(tail) > 1:
            kind = "search"
            query = tail

    return YouTubeIntent(kind, query or None)


def parse_standalone_song_youtube(ql: str, q: str) -> Optional[YouTubeIntent]:
    """e.g. arijit singh song play koro — no explicit 'youtube' but clear play-song intent."""
    if mentions_youtube(q, ql):
        return None
    if not any(k in ql for k in ("song", "gana", "gan ", "play ", "guitar")) and "গান" not in q:
        return None
    if "play" not in ql and "চাল" not in q and "koro" not in ql and "করো" not in q:
        return None
    work = q
    for pat in (r"\bplay\b", r"\bsong\b", r"\bvideo\b", r"গান", r"চালাও|চালান|চালাই", r"\bkoro\b", r"করো"):
        work = re.sub(pat, " ", work, flags=re.IGNORECASE)
    work = _norm(re.sub(r"\s+", " ", work).strip())
    work = _strip_filler_words(work, work.lower())
    if len(work) < 2:
        return None
    return YouTubeIntent("play", work)


def _play_first_youtube_result(query: str) -> bool:
    return False


def execute_youtube(user_text: str, default_kind: Kind) -> str:
    """YouTube is blocked in fully offline mode."""
    return block_internet("YouTube")
