from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

LOG = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    snippet: str
    url: str


@dataclass
class SearchResponse:
    query: str
    summary: str
    results: list[SearchResult] = field(default_factory=list)
    search_url: str = ""
    error: str = ""


def search_web(query: str, max_results: int = 5) -> SearchResponse:
    q = (query or "").strip()
    google_url = f"https://www.google.com/search?q={quote_plus(q)}"
    LOG.info("[search] query: %s", q)
    if not q:
        return SearchResponse(q, "Search query is empty.", [], google_url, "empty_query")

    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as exc:
        message = f"Web search dependencies are missing: {exc}"
        LOG.warning("[search] %s", message)
        return SearchResponse(q, "স্যার, ওয়েব সার্চ চালাতে প্রয়োজনীয় প্যাকেজ পাওয়া যায়নি।", [], google_url, message)

    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": q},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                )
            },
            timeout=8,
        )
        response.raise_for_status()
    except Exception as exc:
        message = f"Search request failed: {exc}"
        LOG.warning("[search] %s", message)
        return SearchResponse(q, f"স্যার, ওয়েব সার্চ করতে পারিনি: {q}", [], google_url, message)

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[SearchResult] = []
    for item in soup.select(".result"):
        link = item.select_one(".result__a")
        if link is None:
            continue
        title = link.get_text(" ", strip=True)
        url = _clean_duckduckgo_url(str(link.get("href") or ""))
        snippet_node = item.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        if title and url:
            results.append(SearchResult(title=title, snippet=snippet, url=url))
        if len(results) >= max_results:
            break

    summary = _build_summary(q, results)
    LOG.info("[search] results found: %s", len(results))
    LOG.info("[search] summary: %s", summary)
    return SearchResponse(q, summary, results, google_url, "")


def _clean_duckduckgo_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "uddg" in params and params["uddg"]:
        return unquote(params["uddg"][0])
    return url


def _build_summary(query: str, results: list[SearchResult]) -> str:
    if not results:
        return f"স্যার, {query} বিষয়ে কোনো নির্ভরযোগ্য সার্চ রেজাল্ট পেলাম না।"
    first = results[0]
    if first.snippet:
        return f"{first.snippet} আমি আপনার জন্য কয়েকটি রেজাল্ট দেখাচ্ছি।"
    return f"{first.title}. আমি আপনার জন্য কয়েকটি রেজাল্ট দেখাচ্ছি।"
