"""Form Guide YouTube tutorial recommendation — orchestrates cache lookup, query generation,
the YouTube API client, and the ranking engine. Every failure mode degrades to
`{"available": False, "reason": ...}` rather than raising — the Form Guide this sits alongside
must never be blocked or slowed by this feature (Section 20's "never block the Form Guide").
"""

import logging
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.modules.scheme_kb.service import get_scheme
from app.modules.video_recommendation import client as youtube_client
from app.modules.video_recommendation.client import YouTubeApiError
from app.modules.video_recommendation.engine import build_search_query, select_best_video

logger = logging.getLogger(__name__)


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_out(doc: dict) -> dict:
    if not doc.get("available"):
        return {"available": False, "reason": doc.get("reason") or "Video tutorial unavailable", "cached": doc.get("cached", False)}
    return {
        "available": True,
        "video_id": doc["youtube_video_id"],
        "title": doc["video_title"],
        "channel_title": doc.get("channel_title"),
        "thumbnail_url": doc.get("thumbnail_url"),
        "youtube_url": doc["youtube_url"],
        "view_count": doc.get("view_count"),
        "like_count": doc.get("like_count"),
        "relevance_score": doc.get("relevance_score"),
        "cached": doc.get("cached", False),
        "last_verified_at": doc.get("last_verified_at"),
    }


async def _fetch_and_rank(scheme: dict) -> dict:
    """Returns a cache-document-shaped dict (not yet the API response shape) describing either
    a found video or an honest not-found reason — never raises."""
    settings = get_settings()
    if not settings.youtube_api_key:
        return {"available": False, "reason": "Video tutorials are not configured for this platform."}

    query = build_search_query(scheme["name"], scheme.get("category"), scheme.get("issuing_authority"))
    try:
        candidate_ids = await youtube_client.search_videos(query, settings.youtube_api_key)
        if not candidate_ids:
            return {"available": False, "reason": "No suitable video tutorial found."}
        candidates = await youtube_client.get_video_details(candidate_ids, settings.youtube_api_key)
    except YouTubeApiError:
        logger.warning("YouTube API call failed for scheme %s; Form Guide continues without a video.", scheme["id"], exc_info=True)
        return {"available": False, "reason": "Video tutorial unavailable right now."}

    for c in candidates:
        c["published_at"] = _parse_published_at(c.get("published_at"))

    best = select_best_video(candidates, scheme["name"], scheme.get("category"))
    if best is None:
        return {"available": False, "reason": "No suitable video tutorial found."}

    return {
        "available": True,
        "youtube_video_id": best["video_id"],
        "video_title": best["title"],
        "channel_title": best.get("channel_title"),
        "thumbnail_url": best.get("thumbnail_url"),
        "youtube_url": f"https://www.youtube.com/watch?v={best['video_id']}",
        "view_count": best.get("view_count"),
        "like_count": best.get("like_count"),
        "relevance_score": round(best["overall"], 4),
        "search_query_used": query,
    }


async def get_video_recommendation(db: AsyncIOMotorDatabase, scheme_id: str) -> dict:
    scheme = await get_scheme(db, scheme_id)  # 404s if the scheme itself doesn't exist
    settings = get_settings()

    cached = await db.video_recommendations.find_one({"scheme_id": scheme_id})
    if cached is not None:
        last_verified_at = cached["last_verified_at"]
        if last_verified_at.tzinfo is None:
            last_verified_at = last_verified_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_verified_at
        if age < timedelta(days=settings.youtube_video_cache_ttl_days):
            return _to_out({**cached, "cached": True})

    result = await _fetch_and_rank(scheme)
    now = datetime.now(timezone.utc)
    doc = {**result, "scheme_id": scheme_id, "last_verified_at": now}
    await db.video_recommendations.update_one({"scheme_id": scheme_id}, {"$set": doc}, upsert=True)
    return _to_out({**doc, "cached": False})
