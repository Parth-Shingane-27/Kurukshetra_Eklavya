import asyncio
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.models.nl_search import NLSearchDraft
from app.modules.scheme_kb.service import get_scheme, list_schemes

logger = logging.getLogger(__name__)

NL_PARSE_TIMEOUT_SECONDS = 8
"""A natural-language parse is a convenience layer on top of the always-working keyword
search (search_catalog, below) — bounding it tightly means an unavailable/rate-limited LLM
never makes catalog search itself feel slow or broken, unlike the longer waits accepted
elsewhere in this app for features with no non-AI fallback."""


async def search_catalog(
    db: AsyncIOMotorDatabase,
    query: str | None = None,
    category: str | None = None,
    state: str | None = None,
) -> list[dict]:
    """FR-014: extends FR-003's scheme listing with a keyword search, reusing
    `scheme_kb.service.list_schemes` for the category/state filtering (BR-003's active-only
    scoping included) rather than a second, divergent listing query. `query` matches against
    name, description, category, and issuing_authority — case-insensitive substring, not a
    full inverted index, since the catalog is expected to stay in the hundreds of schemes
    (NFR-001/NFR-002). No matches is a valid, empty result — never an error."""
    schemes = await list_schemes(db, category=category, state=state, include_inactive=False)

    if not query:
        return schemes

    needle = query.strip().lower()
    if not needle:
        return schemes

    def matches(scheme: dict) -> bool:
        haystacks = [
            scheme.get("name") or "",
            scheme.get("description") or "",
            scheme.get("category") or "",
            scheme.get("issuing_authority") or "",
        ]
        return any(needle in h.lower() for h in haystacks)

    return [s for s in schemes if matches(s)]


async def _parse_natural_language_query(text: str) -> NLSearchDraft | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    try:
        async def _call():
            llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
            structured_llm = llm.with_structured_output(NLSearchDraft)
            prompt = (
                "Extract a search topic and an Indian state (if mentioned) from this citizen's "
                "request for a government scheme. The topic should be the core subject only — "
                "strip out filler words and the state name itself.\n\n"
                f"Request: {text}"
            )
            result = await structured_llm.ainvoke(prompt)
            return result if isinstance(result, NLSearchDraft) else NLSearchDraft.model_validate(result)

        return await asyncio.wait_for(_call(), timeout=NL_PARSE_TIMEOUT_SECONDS)
    except Exception:
        logger.info("Natural-language search parse unavailable/timed out; falling back to keyword search.", exc_info=True)
        return None


async def natural_language_search(db: AsyncIOMotorDatabase, text: str) -> dict:
    draft = await _parse_natural_language_query(text)
    if draft is not None:
        schemes = await search_catalog(db, query=draft.topic, state=draft.state)
        return {
            "interpreted_topic": draft.topic,
            "interpreted_state": draft.state,
            "used_ai": True,
            "schemes": schemes,
        }

    schemes = await search_catalog(db, query=text)
    return {
        "interpreted_topic": text,
        "interpreted_state": None,
        "used_ai": False,
        "schemes": schemes,
    }


async def get_scheme_guide(db: AsyncIOMotorDatabase, scheme_id: str) -> dict:
    """FR-014: retrieve one scheme's form-filling guide. 404s only when the scheme itself
    doesn't exist (TC-032) — a scheme with no authored guide yet returns `guide: null` rather
    than a 404, since the scheme itself is real, only its guide content is not yet written."""
    scheme = await get_scheme(db, scheme_id)
    return {
        "scheme_id": scheme["id"],
        "scheme_name": scheme["name"],
        "guide": scheme.get("guide"),
        "official_scheme_url": (scheme.get("links") or {}).get("official_scheme_url"),
        "application_url": (scheme.get("links") or {}).get("application_url"),
        "application_link_status": (scheme.get("links") or {}).get("application_link_status"),
    }
