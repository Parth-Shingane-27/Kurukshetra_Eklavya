"""Reviewer-facing summary of an already-computed fraud-risk screening (Section 7.5: "An LLM
may summarize evidence, but it must not invent fraud indicators"). Same discipline as
explanation/engine.py's template + explanation/llm_client.py's prompt: restate only the given
structured indicators, never add a new one."""

import asyncio
import logging

from app.modules.explanation.llm_client import call_gemini

logger = logging.getLogger(__name__)


def build_template_summary(screening: dict) -> str:
    indicators = screening["indicators"]
    if not indicators:
        return "No fraud risk indicators were found. Risk level: low. No human review required."
    lines = [f"Risk level: {screening['risk_level']}. Human review required: yes.", "Indicators found:"]
    for indicator in indicators:
        lines.append(f"- {indicator['type']}: {indicator['detail']}")
    return "\n".join(lines)


def build_summary_prompt(screening: dict) -> str:
    lines = [
        "You are writing a short note for a human reviewer summarizing fraud-risk indicators "
        "already computed by a deterministic system. You must ONLY restate the indicators "
        "listed below - do not infer, add, or imply any indicator not explicitly given, and "
        "never state that fraud is confirmed (only a human reviewer can decide that).",
        "",
        f"Risk level: {screening['risk_level']}",
        "Indicators:",
    ]
    for indicator in screening["indicators"]:
        lines.append(f"- {indicator['type']}: {indicator['detail']}")
    lines.append("")
    lines.append("Write 2-3 plain-language sentences for the reviewer. Do not use markdown.")
    return "\n".join(lines)


async def generate_fraud_summary(screening: dict, api_key: str | None, model: str, timeout_seconds: float = 15.0) -> str:
    if api_key:
        try:
            prompt = build_summary_prompt(screening)
            return await asyncio.wait_for(call_gemini(prompt, api_key, model), timeout=timeout_seconds)
        except Exception:
            logger.warning("Gemini fraud-summary call failed; using template fallback.", exc_info=True)
    return build_template_summary(screening)
