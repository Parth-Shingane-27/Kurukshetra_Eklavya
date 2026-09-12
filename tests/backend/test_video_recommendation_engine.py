"""Form Guide YouTube ranking engine — pure functions, no network/mocks needed."""

from datetime import datetime, timedelta, timezone

from app.modules.video_recommendation.engine import (
    build_search_query,
    keyword_relevance,
    recency_score,
    select_best_video,
    title_relevance,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _video(title, description="", view_count=0, like_count=0, days_old=30, video_id="v1"):
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "view_count": view_count,
        "like_count": like_count,
        "published_at": NOW - timedelta(days=days_old),
    }


def test_build_search_query_is_specific_not_generic():
    query = build_search_query("PM-KISAN Samman Nidhi", category="Agriculture,Rural & Environment")
    assert "PM-KISAN Samman Nidhi" in query
    assert "Agriculture" in query
    assert "registration form filling online application" in query
    assert query != "how to fill form"


def test_build_search_query_handles_missing_category():
    query = build_search_query("Some Scheme")
    assert "Some Scheme" in query


def test_title_relevance_scores_higher_for_matching_title():
    ref = {"pmkisan", "samman", "nidhi"}
    high = title_relevance(ref, "PM Kisan Samman Nidhi Registration Form Kaise Bhare")
    low = title_relevance(ref, "Top 10 Bollywood Movies of 2025")
    assert high > low
    assert high > 0.5
    assert low == 0.0


def test_keyword_relevance_detects_howto_phrases():
    high = keyword_relevance("How to apply online registration form filling process", "")
    low = keyword_relevance("Random vlog about my day", "")
    assert high > low
    assert high == 1.0


def test_recency_score_prefers_newer_videos():
    fresh = recency_score(NOW - timedelta(days=30), now=NOW)
    old = recency_score(NOW - timedelta(days=3650), now=NOW)
    assert fresh > old
    assert old == 0.0  # floored, never negative


def test_select_best_video_prefers_relevant_over_popular_but_unrelated():
    relevant = _video(
        "PM-KISAN Samman Nidhi Registration Form Filling Online Application",
        description="Step by step guide to apply for PM Kisan",
        view_count=5000, like_count=200, days_old=100, video_id="relevant",
    )
    popular_unrelated = _video(
        "Top 10 Bollywood Songs 2025", view_count=50_000_000, like_count=2_000_000, days_old=10, video_id="popular"
    )
    best = select_best_video([relevant, popular_unrelated], "PM-KISAN Samman Nidhi", category="Agriculture")
    assert best is not None
    assert best["video_id"] == "relevant"


def test_select_best_video_returns_none_when_all_below_threshold():
    weak = _video("Completely unrelated cooking recipe video", view_count=10, like_count=1, days_old=1000)
    best = select_best_video([weak], "PM-KISAN Samman Nidhi", category="Agriculture")
    assert best is None


def test_select_best_video_returns_none_for_empty_list():
    assert select_best_video([], "Some Scheme") is None


def test_views_and_likes_break_ties_among_similarly_relevant_videos():
    a = _video(
        "PM-KISAN Samman Nidhi Registration Form Filling",
        view_count=1000, like_count=50, days_old=200, video_id="a",
    )
    b = _video(
        "PM-KISAN Samman Nidhi Registration Form Filling",
        view_count=100_000, like_count=5000, days_old=200, video_id="b",
    )
    best = select_best_video([a, b], "PM-KISAN Samman Nidhi", category="Agriculture")
    assert best["video_id"] == "b"
