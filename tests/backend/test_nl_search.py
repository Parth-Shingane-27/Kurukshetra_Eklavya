"""Natural-language catalog search — bounded LLM parse, always falls back to plain keyword
search when unavailable/slow (never blocks or breaks catalog search)."""

from app.core.config import get_settings
from app.models.nl_search import NLSearchDraft
from app.modules.scheme_catalog import service

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}


class _FakeSettingsWithKey:
    gemini_api_key = "fake-key"
    gemini_model = "gemini-2.0-flash"


class _FakeSettingsNoKey:
    gemini_api_key = None
    gemini_model = "gemini-2.0-flash"


class _FakeStructuredLLM:
    def __init__(self, draft=None, raise_error=False, hang=False):
        self._draft = draft
        self._raise_error = raise_error
        self._hang = hang

    async def ainvoke(self, prompt):
        if self._hang:
            import asyncio

            await asyncio.sleep(30)
        if self._raise_error:
            raise RuntimeError("simulated failure")
        return self._draft


class _FakeChatModel:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(**self._kwargs)


def _factory(**kwargs):
    def make(model, google_api_key):
        return _FakeChatModel(**kwargs)

    return make


async def _seed_scheme(client, name, category="Agriculture,Rural & Environment", state=None):
    rules = [{"field_name": "state", "operator": "=", "value": state}] if state else []
    await client.post(
        "/api/schemes",
        json={"name": name, "category": category, "benefit_type": "cash_transfer", "benefit_value_estimate": 1, "rules": rules},
        headers=ADMIN_HEADERS,
    )


async def test_nl_search_uses_ai_parse_when_available(client, monkeypatch):
    await _seed_scheme(client, "Farmer Income Support Scheme", state="Maharashtra")
    await _seed_scheme(client, "Unrelated Housing Scheme")

    monkeypatch.setattr("app.modules.scheme_catalog.service.get_settings", lambda: _FakeSettingsWithKey())
    draft = NLSearchDraft(topic="income support", state="Maharashtra")
    monkeypatch.setattr("app.modules.scheme_catalog.service.ChatGoogleGenerativeAI", _factory(draft=draft), raising=False)

    res = await client.post("/api/catalog/search-natural-language", json={"text": "I'm a farmer needing income support in Maharashtra"})
    assert res.status_code == 200
    body = res.json()
    assert body["used_ai"] is True
    assert body["interpreted_topic"] == "income support"
    assert body["interpreted_state"] == "Maharashtra"
    names = [s["name"] for s in body["schemes"]]
    assert "Farmer Income Support Scheme" in names
    assert "Unrelated Housing Scheme" not in names


async def test_nl_search_falls_back_to_keyword_when_no_api_key(client, monkeypatch):
    await _seed_scheme(client, "Fallback Keyword Test Scheme")

    monkeypatch.setattr("app.modules.scheme_catalog.service.get_settings", lambda: _FakeSettingsNoKey())

    res = await client.post("/api/catalog/search-natural-language", json={"text": "Fallback Keyword Test Scheme"})
    assert res.status_code == 200
    body = res.json()
    assert body["used_ai"] is False
    assert body["interpreted_topic"] == "Fallback Keyword Test Scheme"
    assert any(s["name"] == "Fallback Keyword Test Scheme" for s in body["schemes"])


async def test_nl_search_falls_back_when_llm_raises(client, monkeypatch):
    await _seed_scheme(client, "Error Fallback Test Scheme")
    monkeypatch.setattr("app.modules.scheme_catalog.service.get_settings", lambda: _FakeSettingsWithKey())
    monkeypatch.setattr(
        "app.modules.scheme_catalog.service.ChatGoogleGenerativeAI", _factory(raise_error=True), raising=False
    )

    res = await client.post("/api/catalog/search-natural-language", json={"text": "Error Fallback Test Scheme"})
    body = res.json()
    assert body["used_ai"] is False
    assert any(s["name"] == "Error Fallback Test Scheme" for s in body["schemes"])


async def test_nl_search_times_out_quickly_when_llm_hangs(client, monkeypatch):
    await _seed_scheme(client, "Timeout Fallback Test Scheme")
    monkeypatch.setattr("app.modules.scheme_catalog.service.get_settings", lambda: _FakeSettingsWithKey())
    monkeypatch.setattr("app.modules.scheme_catalog.service.NL_PARSE_TIMEOUT_SECONDS", 1, raising=False)
    monkeypatch.setattr("app.modules.scheme_catalog.service.ChatGoogleGenerativeAI", _factory(hang=True), raising=False)

    import time

    start = time.monotonic()
    res = await client.post("/api/catalog/search-natural-language", json={"text": "Timeout Fallback Test Scheme"})
    elapsed = time.monotonic() - start

    assert elapsed < 5
    body = res.json()
    assert body["used_ai"] is False
    assert any(s["name"] == "Timeout Fallback Test Scheme" for s in body["schemes"])


async def test_nl_search_no_matches_is_empty_not_error(client, monkeypatch):
    monkeypatch.setattr("app.modules.scheme_catalog.service.get_settings", lambda: _FakeSettingsNoKey())
    res = await client.post("/api/catalog/search-natural-language", json={"text": "no such scheme xyz123"})
    assert res.status_code == 200
    assert res.json()["schemes"] == []
