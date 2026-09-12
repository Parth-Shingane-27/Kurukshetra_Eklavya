"""Form Guide — YouTube tutorial video recommendation (Section 17 of the brief). Purely an
enhancement alongside the existing text/step Form Guide (FR-014's `SchemeGuide`) — never a
replacement, and never something that can block or slow down the guide itself. See
`app/modules/video_recommendation/` for the search/ranking/caching implementation.
"""

from datetime import datetime

from pydantic import BaseModel


class VideoRecommendationOut(BaseModel):
    available: bool
    video_id: str | None = None
    title: str | None = None
    channel_title: str | None = None
    thumbnail_url: str | None = None
    youtube_url: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    relevance_score: float | None = None
    reason: str | None = None
    """Set only when `available` is False — a short, honest explanation (e.g. "YouTube
    integration is not configured", "No suitable video tutorial found") rather than leaving
    the frontend to guess why nothing came back."""
    cached: bool = False
    last_verified_at: datetime | None = None
