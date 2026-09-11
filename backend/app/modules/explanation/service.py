import asyncio
import logging

from app.core.config import get_settings
from app.modules.explanation import llm_client
from app.modules.explanation.engine import build_template_explanation

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 15.0


async def generate_explanation(bundle_result: dict) -> str:
    """FR-007: plain-language explanation of the bundle. Tries Gemini, falls back to the
    deterministic template on any failure/timeout/missing key (BR-010) — this call must
    never raise and never block the pipeline on LLM availability.
    """
    if not bundle_result["included"] and not bundle_result["excluded"]:
        return build_template_explanation(bundle_result)  # nothing to explain, skip the LLM call

    settings = get_settings()
    if settings.gemini_api_key:
        try:
            prompt = llm_client.build_prompt(bundle_result)
            return await asyncio.wait_for(
                llm_client.call_gemini(prompt, settings.gemini_api_key, settings.gemini_model),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.warning("Gemini explanation call failed; using template fallback (BR-010).", exc_info=True)

    return build_template_explanation(bundle_result)
