"""Isolated Gemini API client code — kept separate from service.py so tests can monkeypatch
`call_gemini` directly without needing network access or a real API key.
"""

from google import genai
from google.genai import types


def build_prompt(bundle_result: dict) -> str:
    lines = [
        "You are explaining a government benefits recommendation to a citizen in plain, "
        "friendly language. You must ONLY restate the facts given below - do not invent any "
        "eligibility rule, benefit amount, or conflict that is not listed here.",
        "",
        f"Recommended schemes (total estimated benefit: {bundle_result['total_benefit_value']:,.0f}):",
    ]
    for s in bundle_result["included"]:
        lines.append(f"- {s['scheme_name']} (benefit estimate: {s['benefit_value_estimate']:,.0f})")
    if not bundle_result["included"]:
        lines.append("(none)")

    if bundle_result["excluded"]:
        lines.append("")
        lines.append("Eligible schemes excluded from the bundle due to conflicts:")
        for e in bundle_result["excluded"]:
            lines.append(f"- {e['scheme_name']}: {e['reason']}")

    lines.append("")
    lines.append(
        "Write a short (3-5 sentence) plain-language explanation covering why the recommended "
        "schemes were chosen and why any excluded scheme was left out. Do not use markdown."
    )
    return "\n".join(lines)


async def call_gemini(prompt: str, api_key: str, model_name: str, timeout_ms: int = 10_000) -> str:
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))
    response = await client.aio.models.generate_content(model=model_name, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Empty response from Gemini")
    return text
