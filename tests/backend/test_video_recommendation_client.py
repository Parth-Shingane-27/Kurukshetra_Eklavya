"""YouTube Data API v3 client — HTTP-level error handling, mocked via monkeypatched httpx."""

import httpx
import pytest

from app.modules.video_recommendation import client as youtube_client
from app.modules.video_recommendation.client import YouTubeApiError


class _FakeResponse:
    def __init__(self, status_code, json_body=None):
        self.status_code = status_code
        self._json_body = json_body or {}

    def json(self):
        return self._json_body


class _FakeAsyncClient:
    def __init__(self, response=None, raise_error=None):
        self._response = response
        self._raise_error = raise_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        if self._raise_error:
            raise self._raise_error
        return self._response


async def test_search_videos_parses_video_ids(monkeypatch):
    response = _FakeResponse(200, {"items": [{"id": {"videoId": "abc"}}, {"id": {"videoId": "def"}}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response))

    ids = await youtube_client.search_videos("test query", "fake-key")
    assert ids == ["abc", "def"]


async def test_search_videos_raises_on_403(monkeypatch):
    response = _FakeResponse(403, {})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response))

    with pytest.raises(YouTubeApiError, match="invalid or quota"):
        await youtube_client.search_videos("test query", "bad-key")


async def test_search_videos_raises_on_network_failure(monkeypatch):
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(raise_error=httpx.ConnectError("no network"))
    )
    with pytest.raises(YouTubeApiError):
        await youtube_client.search_videos("test query", "fake-key")


async def test_search_videos_raises_on_malformed_response(monkeypatch):
    response = _FakeResponse(200, {"items": [{"unexpected": "shape"}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response))

    # Missing videoId entries are just skipped, not an error — this is a valid, if odd, response.
    ids = await youtube_client.search_videos("test query", "fake-key")
    assert ids == []


async def test_get_video_details_filters_non_public_videos(monkeypatch):
    body = {
        "items": [
            {
                "id": "public1",
                "snippet": {"title": "Public Video", "channelTitle": "Ch", "thumbnails": {}, "publishedAt": "2024-01-01T00:00:00Z"},
                "statistics": {"viewCount": "100", "likeCount": "10"},
                "status": {"privacyStatus": "public", "uploadStatus": "processed"},
            },
            {
                "id": "private1",
                "snippet": {"title": "Private Video", "channelTitle": "Ch", "thumbnails": {}, "publishedAt": "2024-01-01T00:00:00Z"},
                "statistics": {"viewCount": "5", "likeCount": "1"},
                "status": {"privacyStatus": "private", "uploadStatus": "processed"},
            },
        ]
    }
    response = _FakeResponse(200, body)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response))

    results = await youtube_client.get_video_details(["public1", "private1"], "fake-key")
    assert len(results) == 1
    assert results[0]["video_id"] == "public1"
    assert results[0]["view_count"] == 100


async def test_get_video_details_empty_ids_returns_empty_without_a_call(monkeypatch):
    def _should_not_be_called(**kwargs):
        raise AssertionError("httpx.AsyncClient should not be constructed for an empty id list")

    monkeypatch.setattr(httpx, "AsyncClient", _should_not_be_called)
    results = await youtube_client.get_video_details([], "fake-key")
    assert results == []
