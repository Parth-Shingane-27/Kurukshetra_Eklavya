"""Isolated Tavily web-search client code — kept separate from any caller so tests can
monkeypatch `search_scheme_info` directly without needing network access or a real API key,
the same pattern app/modules/video_recommendation/client.py already uses for the YouTube API.

Results from this client are never trusted directly as "official" — every caller must treat
them as unverified source material to feed into the existing curator-review pipelines
(rag_refresh / scheme_discovery), never as something written straight to a live scheme.
"""

import httpx

SEARCH_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESULTS = 5


class TavilySearchError(Exception):
    """Wraps any Tavily API failure (bad key, network error, malformed response) into one
    type — callers only need to catch this once and degrade gracefully (e.g. fall back to the
    local corpus, or produce no candidate), never letting a raw httpx/JSON exception escape."""


async def search_scheme_info(query: str, api_key: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """Returns live web search results for a scheme-related query. Each result is
    {"title": str, "url": str, "content": str}. Raises TavilySearchError on any failure —
    callers must catch it and degrade (this must never surface as an app-facing error)."""
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "include_answer": False,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(SEARCH_URL, json=payload)
    except httpx.HTTPError as exc:
        raise TavilySearchError(f"Tavily search request failed: {exc}") from exc

    if response.status_code == 401:
        raise TavilySearchError("Tavily API key invalid")
    if response.status_code != 200:
        raise TavilySearchError(f"Tavily search returned HTTP {response.status_code}")

    try:
        body = response.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item["url"],
                "content": item.get("content", ""),
            }
            for item in body.get("results", [])
            if item.get("url")
        ]
    except (KeyError, ValueError) as exc:
        raise TavilySearchError(f"Malformed Tavily search response: {exc}") from exc
