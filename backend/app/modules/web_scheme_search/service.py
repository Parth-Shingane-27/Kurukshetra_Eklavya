"""Personalized live web scheme search for a citizen's own dashboard — distinct from
`app.modules.scheme_discovery`, which queues proposals for admin approval before they ever
become a real scheme. Here, drafted suggestions are returned directly to the citizen who
triggered the search (always labeled unverified on the frontend) and never written to the
curated `schemes` collection.

Cached per-citizen in `web_scheme_suggestions` with a TTL (`settings.web_scheme_cache_ttl_hours`)
so a dashboard load doesn't re-run Tavily/Gemini every time. Failure handling mirrors
`scheme_discovery.discover_schemes` exactly: no Tavily key, no Gemini key, a search failure, a
drafting failure, or nothing confidently drafted all degrade to the existing cache (marked
stale) or an empty result — never an exception, never a guess.
"""

import logging
from datetime import datetime, timedelta, timezone

from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.models.scheme_discovery import SchemeDiscoveryDraftList
from app.modules.scheme_kb.service import list_schemes
from app.modules.web_search.client import TavilySearchError, search_scheme_info

logger = logging.getLogger(__name__)

MAX_WEB_RESULTS = 8


def _build_query(citizen: dict) -> str:
    parts = ["government welfare schemes for"]
    parts.append(citizen.get("occupation") or "citizens")
    state = citizen.get("state")
    if state:
        parts.append(f"in {state}, India")
    else:
        parts.append("in India")

    hints = []
    if citizen.get("bpl_status"):
        hints.append("BPL households")
    if citizen.get("disability_status"):
        hints.append("persons with disabilities")
    social_category = citizen.get("social_category")
    if social_category and social_category.upper() not in {"GENERAL", "NONE"}:
        hints.append(f"{social_category} category")
    employment_status = citizen.get("employment_status")
    if employment_status:
        hints.append(employment_status.replace("_", " "))
    if hints:
        parts.append("for " + " and ".join(hints))

    return " ".join(parts)


def _build_prompt(query: str, existing_names: list[str], evidence_text: str) -> str:
    return (
        "You are surfacing PROPOSED government-scheme information directly to the citizen who "
        "searched for it — you are NOT publishing anything, NOT making an eligibility decision, "
        "and this is explicitly labeled unverified to them. Only include a scheme that the "
        "retrieved text below clearly describes as a real, named government scheme/policy with "
        "its own eligibility or benefit; do not invent one. Only propose a value for a field if "
        "the text clearly supports it for THAT scheme; leave a field null rather than guess. "
        "Never invent a benefit amount or URL that isn't grounded in the text below. Skip any "
        "scheme whose name closely matches one already in the catalogue (listed below).\n\n"
        f"Search query: {query}\n"
        f"Schemes already in the catalogue (do not re-propose these): {existing_names}\n\n"
        f"Retrieved web text:\n{evidence_text}\n"
    )


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def get_personalized_web_schemes(db: AsyncIOMotorDatabase, citizen: dict, force: bool = False) -> dict:
    settings = get_settings()
    citizen_id = citizen["id"]
    cached = await db.web_scheme_suggestions.find_one({"citizen_id": citizen_id})

    if cached and not force:
        age = datetime.now(timezone.utc) - cached["generated_at"].replace(tzinfo=timezone.utc)
        if age < timedelta(hours=settings.web_scheme_cache_ttl_hours):
            return _serialize(cached)

    if not settings.tavily_api_key or not settings.gemini_api_key:
        logger.info("Web scheme search: TAVILY_API_KEY/GEMINI_API_KEY not configured; skipping.")
        return _degraded_result(citizen_id, cached)

    query = _build_query(citizen)
    try:
        web_results = await search_scheme_info(query, settings.tavily_api_key, max_results=MAX_WEB_RESULTS)
    except TavilySearchError:
        logger.warning("Web scheme search: Tavily search failed for citizen %s.", citizen_id, exc_info=True)
        return _degraded_result(citizen_id, cached, query=query)

    if not web_results:
        return _degraded_result(citizen_id, cached, query=query)

    existing = await list_schemes(db, include_inactive=True)
    existing_names = [s["name"] for s in existing]
    evidence_text = "\n".join(f"- {r['content'] or r['title']} (source: {r['url']})" for r in web_results)
    prompt = _build_prompt(query, existing_names, evidence_text)

    try:
        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        structured_llm = llm.with_structured_output(SchemeDiscoveryDraftList)
        draft_result = await structured_llm.ainvoke(prompt)
        draft_list = (
            draft_result
            if isinstance(draft_result, SchemeDiscoveryDraftList)
            else SchemeDiscoveryDraftList.model_validate(draft_result)
        )
    except Exception:
        logger.warning("Web scheme search: drafting pass failed for citizen %s.", citizen_id, exc_info=True)
        return _degraded_result(citizen_id, cached, query=query)

    existing_lower = {n.strip().lower() for n in existing_names}
    suggestions = [
        draft.model_dump(exclude_none=False)
        for draft in draft_list.schemes
        if draft.name.strip().lower() not in existing_lower
    ]

    doc = {
        "citizen_id": citizen_id,
        "query": query,
        "generated_at": datetime.now(timezone.utc),
        "suggestions": suggestions,
        "stale": False,
    }
    await db.web_scheme_suggestions.update_one({"citizen_id": citizen_id}, {"$set": doc}, upsert=True)
    return doc


def _degraded_result(citizen_id: str, cached: dict | None, query: str = "") -> dict:
    """Serves the existing cache (marked stale) when a fresh search couldn't run, or an empty
    result if there's no cache yet — never raises, never fabricates a result."""
    if cached:
        result = _serialize(cached)
        result["stale"] = True
        return result
    return {
        "citizen_id": citizen_id,
        "query": query,
        "generated_at": datetime.now(timezone.utc),
        "suggestions": [],
        "stale": True,
    }
