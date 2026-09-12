"""Form Guide YouTube tutorial recommendation — API/service tests. Mocks the YouTube client
(client.py) directly, the same isolation pattern app/modules/explanation/llm_client.py's own
tests already use for Gemini — no real network access, no real API key required."""

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.modules.video_recommendation import client as youtube_client
from app.modules.video_recommendation import service as video_service
from app.modules.video_recommendation.client import YouTubeApiError

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}


class _FakeSettingsWithKey:
    youtube_api_key = "fake-yt-key"
    youtube_video_cache_ttl_days = 30


class _FakeSettingsNoKey:
    youtube_api_key = None
    youtube_video_cache_ttl_days = 30


async def _create_scheme(client, name="Video Test Scheme"):
    res = await client.post(
        "/api/schemes",
        json={"name": name, "category": "Agriculture,Rural & Environment", "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    return res.json()["id"]


def _sample_details(video_id="abc123", title="Video Test Scheme Registration Form Filling Online"):
    return [
        {
            "video_id": video_id,
            "title": title,
            "description": "Step by step guide for the registration form, application process.",
            "channel_title": "Sample Channel",
            "thumbnail_url": "https://img.youtube.com/vi/abc123/hqdefault.jpg",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
            "view_count": 10000,
            "like_count": 500,
        }
    ]


async def test_no_api_key_returns_unavailable_without_error(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsNoKey())

    res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False
    assert "not configured" in body["reason"]


async def test_successful_recommendation_returns_video(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_search(query, api_key):
        assert "Video Test Scheme" in query
        return ["abc123"]

    async def fake_details(ids, api_key):
        return _sample_details()

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)
    monkeypatch.setattr(youtube_client, "get_video_details", fake_details)

    res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is True
    assert body["video_id"] == "abc123"
    assert body["youtube_url"] == "https://www.youtube.com/watch?v=abc123"
    assert body["cached"] is False


async def test_second_request_is_served_from_cache(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    call_count = {"n": 0}

    async def fake_search(query, api_key):
        call_count["n"] += 1
        return ["abc123"]

    async def fake_details(ids, api_key):
        return _sample_details()

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)
    monkeypatch.setattr(youtube_client, "get_video_details", fake_details)

    first = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert first.json()["cached"] is False
    second = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert second.json()["cached"] is True
    assert call_count["n"] == 1  # YouTube was only actually queried once


async def test_no_search_results_returns_unavailable(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_search(query, api_key):
        return []

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)

    res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    body = res.json()
    assert body["available"] is False
    assert "No suitable video" in body["reason"]


async def test_weakly_related_results_return_unavailable_not_a_bad_match(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_search(query, api_key):
        return ["unrelated1"]

    async def fake_details(ids, api_key):
        return [
            {
                "video_id": "unrelated1",
                "title": "Completely unrelated cooking recipe",
                "description": "",
                "channel_title": "Random Channel",
                "thumbnail_url": None,
                "published_at": (datetime.now(timezone.utc) - timedelta(days=2000)).isoformat().replace("+00:00", "Z"),
                "view_count": 5,
                "like_count": 0,
            }
        ]

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)
    monkeypatch.setattr(youtube_client, "get_video_details", fake_details)

    res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    body = res.json()
    assert body["available"] is False
    assert "No suitable video" in body["reason"]


async def test_youtube_api_error_degrades_gracefully(client, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_search(query, api_key):
        raise YouTubeApiError("quota exceeded")

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)

    res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False
    assert "unavailable" in body["reason"]


async def test_unknown_scheme_returns_404(client):
    res = await client.get("/api/catalog/schemes/000000000000000000000000/video-tutorial")
    assert res.status_code == 404


async def test_guide_endpoint_and_form_guide_still_work_when_video_recommendation_fails(client, monkeypatch):
    """The most important regression check: Form Guide itself (FR-014's existing endpoint)
    must be completely unaffected by anything happening in the video-recommendation module."""
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(video_service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_search(query, api_key):
        raise YouTubeApiError("network failure")

    monkeypatch.setattr(youtube_client, "search_videos", fake_search)

    video_res = await client.get(f"/api/catalog/schemes/{scheme_id}/video-tutorial")
    assert video_res.json()["available"] is False

    guide_res = await client.get(f"/api/catalog/schemes/{scheme_id}/guide")
    assert guide_res.status_code == 200
