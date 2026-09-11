"""Multi-language Chat Agent (Section 7.4). Stateless — no new Mongo collection.

Two independent LLM steps, each with an honest no-op fallback rather than a guess:
1. Incoming message: detect language + translate to English (structured output via
   LangChain, so downstream intent routing/retrieval always works against English text).
2. Outgoing response: translate the already-computed `final_response` text back into the
   user's language — but only after verifying every "critical value" (a scheme name, amount,
   date, or document name pulled from already-computed state) still appears verbatim in the
   translated text. A translation that drops/mangles one of those values is worse than no
   translation, so the guard failing means falling back to English with a warning
   (Section 7.4: "Do not translate eligibility logic loosely").
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.modules.explanation.llm_client import call_gemini
from app.modules.multilingual.schemas import DetectAndTranslate

logger = logging.getLogger(__name__)


async def detect_and_translate_to_english(text: str, api_key: str | None, model: str) -> DetectAndTranslate:
    if not api_key or not text.strip():
        return DetectAndTranslate(detected_language="en", translated_text=text)
    try:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
        structured_llm = llm.with_structured_output(DetectAndTranslate)
        prompt = (
            "Detect the language of the following user message and translate it to English. "
            "Preserve proper nouns, scheme names, numbers, and dates exactly as written in "
            f"the translation.\n\nMessage: {text}"
        )
        result = await structured_llm.ainvoke(prompt)
        if isinstance(result, DetectAndTranslate):
            return result
        return DetectAndTranslate.model_validate(result)
    except Exception:
        logger.warning("Language detection/translation failed; treating message as English.", exc_info=True)
        return DetectAndTranslate(detected_language="unknown", translated_text=text)


def _build_translation_prompt(text: str, target_language: str) -> str:
    return (
        f"Translate the following text into {target_language}. Preserve every proper noun, "
        "scheme name, number, date, and document name exactly as written - do not localize "
        f"or reformat them. Do not add commentary.\n\nText: {text}"
    )


async def translate_response(
    text: str,
    target_language: str,
    critical_values: list[str],
    api_key: str | None,
    model: str,
) -> dict:
    if not text.strip() or target_language.lower() in ("en", "english", "unknown") or not api_key:
        return {"text": text, "translated": False, "warning": None}

    try:
        translated = await call_gemini(_build_translation_prompt(text, target_language), api_key, model)
    except Exception:
        logger.warning("Response translation failed; showing English.", exc_info=True)
        return {"text": text, "translated": False, "warning": "Translation unavailable; showing English."}

    missing = [v for v in critical_values if v and v not in translated]
    if missing:
        return {
            "text": text,
            "translated": False,
            "warning": (
                f"Translation guard failed (critical value(s) not preserved: {', '.join(missing)}); "
                "showing English to avoid a corrupted translation."
            ),
        }
    return {"text": translated, "translated": True, "warning": None}
