"""Fraud Detection Agent — summary generation tests. Mirrors explanation/service.py's
LLM-success/failure/no-key coverage: the summary must only restate given indicators, never
invent one, and must fall back to a deterministic template on any LLM failure (BR-010 pattern)."""

import pytest

from app.modules.fraud_detection.summary import build_template_summary, generate_fraud_summary

LOW_RISK = {"indicators": [], "risk_level": "low", "human_review_required": False}
HIGH_RISK = {
    "indicators": [{"type": "date_inconsistency", "detail": "1 document(s) are expired."}],
    "risk_level": "high",
    "human_review_required": True,
}


def test_template_summary_low_risk():
    text = build_template_summary(LOW_RISK)
    assert "low" in text
    assert "No fraud risk indicators" in text


def test_template_summary_lists_indicators_verbatim():
    text = build_template_summary(HIGH_RISK)
    assert "date_inconsistency" in text
    assert "1 document(s) are expired." in text
    assert "high" in text


async def test_generate_summary_uses_template_when_no_api_key():
    text = await generate_fraud_summary(HIGH_RISK, api_key=None, model="gemini-2.0-flash")
    assert text == build_template_summary(HIGH_RISK)


async def test_generate_summary_falls_back_on_llm_failure(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.modules.fraud_detection.summary.call_gemini", _boom)
    text = await generate_fraud_summary(HIGH_RISK, api_key="fake-key", model="gemini-2.0-flash")
    assert text == build_template_summary(HIGH_RISK)
