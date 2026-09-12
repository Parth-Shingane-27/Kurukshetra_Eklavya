"""Isolated YouTube Data API v3 client code — kept separate from service.py so tests can
monkeypatch `search_videos`/`get_video_details` directly without needing network access or a
real API key, the same pattern app/modules/explanation/llm_client.py already uses for Gemini.

Only two endpoints are used, exactly as the brief specifies: `search.list` to discover
candidates, `videos.list` (batched — one call for every candidate's statistics/snippet/status,
never one call per video) to get the metadata the ranking engine needs.
"""

import httpx

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_SEARCH_RESULTS = 10


class YouTubeApiError(Exception):
    """Wraps any YouTube API failure (bad key, quota exceeded, network error, malformed
    response) into one type — service.py only needs to catch this once and degrade to
    "video tutorial unavailable" (Section 9), never letting a raw httpx/JSON exception escape
    into the Form Guide's response path."""


async def search_videos(query: str, api_key: str) -> list[str]:
    """Returns candidate video IDs for a query. Raises YouTubeApiError on any failure."""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": MAX_SEARCH_RESULTS,
        "safeSearch": "moderate",
        "relevanceLanguage": "en",
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(SEARCH_URL, params=params)
    except httpx.HTTPError as exc:
        raise YouTubeApiError(f"YouTube search request failed: {exc}") from exc

    if response.status_code == 403:
        raise YouTubeApiError("YouTube API key invalid or quota exceeded")
    if response.status_code != 200:
        raise YouTubeApiError(f"YouTube search returned HTTP {response.status_code}")

    try:
        body = response.json()
        return [item["id"]["videoId"] for item in body.get("items", []) if item.get("id", {}).get("videoId")]
    except (KeyError, ValueError) as exc:
        raise YouTubeApiError(f"Malformed YouTube search response: {exc}") from exc


async def get_video_details(video_ids: list[str], api_key: str) -> list[dict]:
    """Batched metadata lookup — one request for every id in `video_ids` (YouTube's `videos.list`
    accepts a comma-joined id list natively), never a request per video. Filters out videos
    that aren't public (private/deleted videos never come back from `videos.list` at all, but
    an explicit status check is kept for anything YouTube does return with a non-"public"
    privacyStatus)."""
    if not video_ids:
        return []
    params = {
        "part": "snippet,statistics,status,contentDetails",
        "id": ",".join(video_ids),
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(VIDEOS_URL, params=params)
    except httpx.HTTPError as exc:
        raise YouTubeApiError(f"YouTube videos request failed: {exc}") from exc

    if response.status_code == 403:
        raise YouTubeApiError("YouTube API key invalid or quota exceeded")
    if response.status_code != 200:
        raise YouTubeApiError(f"YouTube videos lookup returned HTTP {response.status_code}")

    try:
        body = response.json()
        results = []
        for item in body.get("items", []):
            status = item.get("status", {})
            if status.get("privacyStatus") not in (None, "public"):
                continue
            if status.get("uploadStatus") not in (None, "processed"):
                continue
            snippet = item["snippet"]
            statistics = item.get("statistics", {})
            results.append(
                {
                    "video_id": item["id"],
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "channel_title": snippet.get("channelTitle"),
                    "thumbnail_url": (snippet.get("thumbnails", {}).get("high") or snippet.get("thumbnails", {}).get("default") or {}).get("url"),
                    "published_at": snippet.get("publishedAt"),
                    "view_count": int(statistics.get("viewCount", 0)),
                    "like_count": int(statistics.get("likeCount", 0)),
                }
            )
        return results
    except (KeyError, ValueError) as exc:
        raise YouTubeApiError(f"Malformed YouTube videos response: {exc}") from exc
