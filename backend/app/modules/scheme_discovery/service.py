"""New-scheme discovery — live web search (Tavily) + LLM drafting, gated behind the same
curator-review-before-trust pattern as app/modules/rag_refresh/service.py. Discovery documents
live ONLY in `scheme_discoveries`; only `approve_discovery` ever writes to the live `schemes`
collection, and it does so through the existing FR-011 `create_scheme` path.

Failure handling mirrors rag_refresh: no Tavily key, no Gemini key, a search failure, a
drafting failure, or a draft with no schemes at all produces an empty result — never a
low-confidence guess and never an exception surfaced past this module.
"""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.models.scheme import SchemeCreate, SchemeDocumentRequirement, SchemeLinks
from app.models.scheme_discovery import SchemeDiscoveryDraftList, SchemeDiscoveryStatus
from app.modules.scheme_kb.service import create_scheme, list_schemes
from app.modules.web_search.client import TavilySearchError, search_scheme_info

logger = logging.getLogger(__name__)


def _to_object_id(discovery_id: str) -> ObjectId:
    try:
        return ObjectId(discovery_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Discovery not found")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _build_prompt(query: str, category: str | None, existing_names: list[str], evidence_text: str) -> str:
    return (
        "You are drafting PROPOSED new government-scheme records for a human curator to "
        "review — you are NOT publishing anything and this is NOT an eligibility decision. "
        "Only include a scheme that the retrieved text below clearly describes as a real, "
        "named government scheme/policy with its own eligibility or benefit; do not invent one. "
        "Only propose a value for a field if the text clearly supports it for THAT scheme; "
        "leave a field null rather than guess. Never invent a benefit amount or URL that isn't "
        "grounded in the text below. Skip any scheme whose name closely matches one already in "
        "the catalogue (listed below) — this search is only for schemes not yet catalogued.\n\n"
        f"Search query: {query}\n"
        f"Category hint (optional): {category or 'none given'}\n"
        f"Schemes already in the catalogue (do not re-propose these): {existing_names}\n\n"
        f"Retrieved web text:\n{evidence_text}\n"
    )


async def discover_schemes(db: AsyncIOMotorDatabase, query: str, category: str | None = None) -> list[dict]:
    """Searches the live web for scheme information matching `query`, drafts candidate new
    scheme records grounded in that text, and queues each as a pending discovery for curator
    review. Returns [] (no discoveries written) when TAVILY_API_KEY/GEMINI_API_KEY aren't
    configured, the search fails, drafting fails, or nothing confident was drafted."""
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.info("Scheme discovery: TAVILY_API_KEY not configured; no discovery produced.")
        return []
    if not settings.gemini_api_key:
        logger.info("Scheme discovery: GEMINI_API_KEY not configured; no discovery produced.")
        return []

    try:
        web_results = await search_scheme_info(query, settings.tavily_api_key, max_results=8)
    except TavilySearchError:
        logger.warning("Scheme discovery: Tavily search failed for query %r.", query, exc_info=True)
        return []

    if not web_results:
        logger.info("Scheme discovery: no web results for query %r; no discovery produced.", query)
        return []

    existing = await list_schemes(db, include_inactive=True)
    existing_names = [s["name"] for s in existing]

    passages = [{"content": r["content"] or r["title"], "source_url": r["url"]} for r in web_results]
    evidence_text = "\n".join(f"- {p['content']} (source: {p['source_url']})" for p in passages)
    prompt = _build_prompt(query, category, existing_names, evidence_text)

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
        logger.warning("Scheme discovery: drafting pass failed for query %r; no discovery produced.", query, exc_info=True)
        return []

    if not draft_list.schemes:
        logger.info("Scheme discovery: draft proposed no schemes for query %r.", query)
        return []

    now = datetime.now(timezone.utc)
    created_docs: list[dict] = []
    for draft in draft_list.schemes:
        if draft.name.strip().lower() in {n.strip().lower() for n in existing_names}:
            continue
        doc = {
            "query": query,
            "draft": draft.model_dump(exclude_none=False),
            "source_passages": passages,
            "confidence": 0.6,
            "rationale": f"Drafted from {len(passages)} live web search result(s) for query {query!r}.",
            "status": SchemeDiscoveryStatus.pending.value,
            "created_at": now,
            "reviewed_at": None,
            "rejection_reason": None,
        }
        insert_result = await db.scheme_discoveries.insert_one(doc)
        created = await db.scheme_discoveries.find_one({"_id": insert_result.inserted_id})
        created_docs.append(_serialize(created))

    return created_docs


async def get_discovery(db: AsyncIOMotorDatabase, discovery_id: str) -> dict:
    oid = _to_object_id(discovery_id)
    doc = await db.scheme_discoveries.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    return _serialize(doc)


async def list_discoveries(db: AsyncIOMotorDatabase, status: str | None = None) -> list[dict]:
    query = {"status": status} if status else {}
    cursor = db.scheme_discoveries.find(query).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def approve_discovery(db: AsyncIOMotorDatabase, discovery_id: str) -> dict:
    """Commits the discovery's draft through the existing FR-011 `create_scheme` path — the
    only code path in the app that creates a scheme. The discovered `application_url` is never
    marked 'verified' on approval — same rationale as rag_refresh.approve_candidate: a curator
    approving this confirms the draft is a good-faith proposal worth adding to the catalogue,
    not that they personally re-checked the destination page."""
    discovery = await get_discovery(db, discovery_id)
    if discovery["status"] != SchemeDiscoveryStatus.pending.value:
        raise HTTPException(status_code=400, detail="Discovery has already been reviewed")

    draft = discovery["draft"]
    links = draft.get("links") or {}
    scheme = SchemeCreate(
        name=draft["name"],
        description=draft.get("description"),
        issuing_authority=draft.get("issuing_authority"),
        category=draft.get("category") or "uncategorized",
        benefit_type=draft.get("benefit_type") or "unknown",
        benefit_value_estimate=draft.get("benefit_value_estimate") or 0.0,
        links=SchemeLinks(
            official_scheme_url=links.get("official_scheme_url"),
            application_url=links.get("application_url"),
            source_url=links.get("source_url"),
            application_link_status="unverified",
            verification_notes=[
                "Discovered via live web search and approved by a curator on "
                f"{datetime.now(timezone.utc).date().isoformat()}: sourced from search results, "
                "not independently re-verified — status stays 'unverified' rather than being "
                "upgraded automatically. Category/benefit fields may need curator completion."
            ],
        ),
        document_requirements=[
            SchemeDocumentRequirement(document_type=doc_type)
            for doc_type in (draft.get("document_requirements") or [])
        ],
    )
    created_scheme = await create_scheme(db, scheme)

    await db.scheme_discoveries.update_one(
        {"_id": ObjectId(discovery_id)},
        {"$set": {"status": SchemeDiscoveryStatus.approved.value, "reviewed_at": datetime.now(timezone.utc)}},
    )
    result = await get_discovery(db, discovery_id)
    result["created_scheme_id"] = created_scheme["id"]
    return result


async def reject_discovery(db: AsyncIOMotorDatabase, discovery_id: str, reason: str | None) -> dict:
    discovery = await get_discovery(db, discovery_id)
    if discovery["status"] != SchemeDiscoveryStatus.pending.value:
        raise HTTPException(status_code=400, detail="Discovery has already been reviewed")

    await db.scheme_discoveries.update_one(
        {"_id": ObjectId(discovery_id)},
        {
            "$set": {
                "status": SchemeDiscoveryStatus.rejected.value,
                "reviewed_at": datetime.now(timezone.utc),
                "rejection_reason": reason,
            }
        },
    )
    return await get_discovery(db, discovery_id)
