"""Explanation Generator: template fallback (BR-010) and the LLM-success/failure paths (TC-016–017)."""

import pytest

from app.modules.explanation import llm_client, service
from app.modules.explanation.engine import build_template_explanation


def _bundle_result(included=None, excluded=None, total=0):
    return {"total_benefit_value": total, "included": included or [], "excluded": excluded or []}


def test_template_handles_empty_bundle():
    text = build_template_explanation(_bundle_result())
    assert "No schemes were found" in text


def test_template_mentions_included_and_excluded_schemes():
    result = _bundle_result(
        included=[{"scheme_name": "PMAY", "scheme_id": "s1", "benefit_value_estimate": 130000}],
        excluded=[{"scheme_name": "State Housing", "scheme_id": "s2", "reason": "same conflict group as 'PMAY'"}],
        total=130000,
    )
    text = build_template_explanation(result)
    assert "PMAY" in text
    assert "State Housing" in text
    assert "130,000" in text


class _FakeSettingsWithKey:
    gemini_api_key = "fake-key"
    gemini_model = "gemini-2.0-flash"


class _FakeSettingsNoKey:
    gemini_api_key = None
    gemini_model = "gemini-2.0-flash"


async def test_uses_llm_output_on_success(monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    async def fake_call_gemini(prompt, api_key, model_name):
        return "A friendly LLM-generated explanation."

    monkeypatch.setattr(llm_client, "call_gemini", fake_call_gemini)

    result = _bundle_result(included=[{"scheme_name": "PMAY", "scheme_id": "s1", "benefit_value_estimate": 130000}], total=130000)
    text = await service.generate_explanation(result)
    assert text == "A friendly LLM-generated explanation."


async def test_falls_back_to_template_on_llm_failure(monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    async def failing_call_gemini(prompt, api_key, model_name):
        raise RuntimeError("network error")

    monkeypatch.setattr(llm_client, "call_gemini", failing_call_gemini)

    result = _bundle_result(included=[{"scheme_name": "PMAY", "scheme_id": "s1", "benefit_value_estimate": 130000}], total=130000)
    text = await service.generate_explanation(result)
    assert "PMAY" in text  # template fallback, not the (absent) LLM text


async def test_falls_back_to_template_on_llm_timeout(monkeypatch):
    import asyncio

    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    monkeypatch.setattr(service, "LLM_TIMEOUT_SECONDS", 0.01)

    async def slow_call_gemini(prompt, api_key, model_name):
        await asyncio.sleep(1)
        return "too slow"

    monkeypatch.setattr(llm_client, "call_gemini", slow_call_gemini)

    result = _bundle_result(included=[{"scheme_name": "PMAY", "scheme_id": "s1", "benefit_value_estimate": 130000}], total=130000)
    text = await service.generate_explanation(result)
    assert "PMAY" in text


async def test_skips_llm_entirely_when_no_api_key(monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsNoKey())

    called = False

    async def should_not_be_called(*args, **kwargs):
        nonlocal called
        called = True
        return "unused"

    monkeypatch.setattr(llm_client, "call_gemini", should_not_be_called)

    result = _bundle_result(included=[{"scheme_name": "PMAY", "scheme_id": "s1", "benefit_value_estimate": 130000}], total=130000)
    text = await service.generate_explanation(result)
    assert called is False
    assert "PMAY" in text


async def test_skips_llm_for_trivial_empty_bundle(monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    called = False

    async def should_not_be_called(*args, **kwargs):
        nonlocal called
        called = True
        return "unused"

    monkeypatch.setattr(llm_client, "call_gemini", should_not_be_called)

    text = await service.generate_explanation(_bundle_result())
    assert called is False
    assert "No schemes were found" in text
