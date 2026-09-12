"""FR-015 — RAG-Based Knowledge Base Freshness (Section 4/12's BR-015).

Architectural boundary this module exists to enforce (the single most important thing about
this feature, per plan.md): retrieval + LLM drafting can produce a *candidate* update, written
ONLY to `rag_candidate_updates` — never to the live `schemes` collection. Only
`approve_candidate` ever writes to `schemes`, and it does so through the existing FR-011
`update_scheme` path (the same one an admin's manual PUT /api/schemes/:id uses), so there is
exactly one code path that commits a scheme change, not two divergent ones.

Failure handling (NFR-014): a source that can't be retrieved, or a drafting pass that isn't
confident enough to ground any field, produces NO candidate at all — never a low-confidence
guess written for a curator to rubber-stamp, and never an exception that could be mistaken for
a pipeline failure elsewhere. This never touches, blocks, or slows the core eligibility/
conflict/optimization pipeline (FR-004/005/006), which never reads this collection.
"""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.models.rag_candidate import RagCandidateDraft, RagCandidateStatus
from app.models.scheme import SchemeUpdate
from app.modules.scheme_kb.service import get_scheme, update_scheme
from app.modules.web_search.client import TavilySearchError, search_scheme_info
from app.rag.policy_service import get_policy_service

logger = logging.getLogger(__name__)


def _to_object_id(candidate_id: str) -> ObjectId:
    try:
        return ObjectId(candidate_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Candidate update not found")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["scheme_id"] = str(doc["scheme_id"])
    return doc


def _build_prompt(scheme: dict, evidence_text: str) -> str:
    return (
        "You are drafting a PROPOSED update to a government scheme record for a human curator "
        "to review — you are NOT committing anything and this is NOT an eligibility decision. "
        "Only propose a value for a field if the retrieved text below clearly and specifically "
        "supports it for THIS scheme; leave a field null rather than guess. Never invent a "
        "benefit amount, deadline, or URL that isn't grounded in the text below.\n\n"
        f"Scheme: {scheme['name']}\n"
        f"Current benefit_value_estimate on file: {scheme.get('benefit_value_estimate')}\n"
        f"Current application_url on file: {(scheme.get('links') or {}).get('application_url')}\n"
        f"Current document requirements on file: "
        f"{[d['document_type'] for d in scheme.get('document_requirements', [])]}\n\n"
        f"Retrieved policy text:\n{evidence_text}\n"
    )


async def refresh_scheme_candidate(db: AsyncIOMotorDatabase, scheme_id: str) -> dict | None:
    """Retrieve the most relevant indexed passages for one scheme, draft a candidate update
    grounded in that text, and queue it for curator review. Returns None (no candidate
    written) when retrieval finds nothing verified, no GEMINI_API_KEY is configured, drafting
    raises, or the draft proposes no confident changes at all."""
    scheme = await get_scheme(db, scheme_id)  # 404s if the scheme itself doesn't exist

    policy_service = get_policy_service()
    result = await policy_service.retrieve_scheme_details(scheme["name"], filters={"scheme_id": scheme_id})
    passages: list[dict] = []
    if result.verified and result.evidence:
        passages.extend({"content": e.content, "source_url": e.source_url or e.source} for e in result.evidence)

    settings = get_settings()
    if getattr(settings, "tavily_api_key", None):
        try:
            web_results = await search_scheme_info(
                f"{scheme['name']} official application eligibility site:gov.in OR site:nic.in",
                settings.tavily_api_key,
            )
            passages.extend({"content": r["content"] or r["title"], "source_url": r["url"]} for r in web_results)
        except TavilySearchError:
            logger.warning("RAG refresh: Tavily search failed for scheme %s; continuing without it.", scheme_id, exc_info=True)

    if not passages:
        logger.info("RAG refresh: no retrievable evidence for scheme %s; no candidate produced.", scheme_id)
        return None

    if not settings.gemini_api_key:
        logger.info("RAG refresh: GEMINI_API_KEY not configured; no candidate produced.")
        return None

    evidence_text = "\n".join(f"- {p['content']} (source: {p['source_url']})" for p in passages)
    prompt = _build_prompt(scheme, evidence_text)

    try:
        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        structured_llm = llm.with_structured_output(RagCandidateDraft)
        draft_result = await structured_llm.ainvoke(prompt)
        draft = (
            draft_result
            if isinstance(draft_result, RagCandidateDraft)
            else RagCandidateDraft.model_validate(draft_result)
        )
    except Exception:
        logger.warning(
            "RAG refresh: drafting pass failed for scheme %s; no candidate produced.", scheme_id, exc_info=True
        )
        return None

    proposed = draft.proposed_changes.model_dump(exclude_none=True)
    if not proposed:
        logger.info(
            "RAG refresh: draft proposed no confident changes for scheme %s; no candidate produced.", scheme_id
        )
        return None

    now = datetime.now(timezone.utc)
    doc = {
        "scheme_id": ObjectId(scheme_id),
        "scheme_name": scheme["name"],
        "status": RagCandidateStatus.pending.value,
        "proposed_changes": proposed,
        "current_snapshot": {
            "benefit_value_estimate": scheme.get("benefit_value_estimate"),
            "application_url": (scheme.get("links") or {}).get("application_url"),
            "document_requirements": [d["document_type"] for d in scheme.get("document_requirements", [])],
        },
        "source_passages": passages,
        "confidence": draft.confidence,
        "rationale": draft.rationale,
        "created_at": now,
        "reviewed_at": None,
        "rejection_reason": None,
    }
    insert_result = await db.rag_candidate_updates.insert_one(doc)
    created = await db.rag_candidate_updates.find_one({"_id": insert_result.inserted_id})
    return _serialize(created)


async def get_candidate(db: AsyncIOMotorDatabase, candidate_id: str) -> dict:
    oid = _to_object_id(candidate_id)
    doc = await db.rag_candidate_updates.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Candidate update not found")
    return _serialize(doc)


async def list_candidates(db: AsyncIOMotorDatabase, status: str | None = None) -> list[dict]:
    query = {"status": status} if status else {}
    cursor = db.rag_candidate_updates.find(query).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def approve_candidate(db: AsyncIOMotorDatabase, candidate_id: str) -> dict:
    """Commits the candidate's proposed changes through the existing FR-011 `update_scheme`
    path — the only code path in the app that writes to `schemes`. A RAG-sourced
    `application_url` is never auto-marked 'verified' on approval (NFR-016) — a curator
    approving this candidate confirms the *text is a good-faith proposal*, not that they
    personally re-checked the destination page, so it lands as 'unverified'."""
    candidate = await get_candidate(db, candidate_id)
    if candidate["status"] != RagCandidateStatus.pending.value:
        raise HTTPException(status_code=400, detail="Candidate update has already been reviewed")

    proposed = candidate["proposed_changes"]
    scheme_id = candidate["scheme_id"]
    now = datetime.now(timezone.utc)

    top_level_updates: dict = {}
    if "benefit_value_estimate" in proposed:
        top_level_updates["benefit_value_estimate"] = proposed["benefit_value_estimate"]
    if "criteria_summary" in proposed:
        top_level_updates["description"] = proposed["criteria_summary"]

    if "application_url" in proposed or "deadline_text" in proposed:
        scheme = await get_scheme(db, scheme_id)
        existing_notes = list((scheme.get("links") or {}).get("verification_notes") or [])
        links_patch: dict = {}
        if "application_url" in proposed:
            links_patch["application_url"] = proposed["application_url"]
            links_patch["application_link_status"] = "unverified"
            existing_notes.append(
                f"RAG-suggested application_url approved by a curator on {now.date().isoformat()}: "
                "sourced from retrieved policy text, not independently re-verified — status stays "
                "'unverified' rather than being upgraded automatically."
            )
        if "deadline_text" in proposed:
            existing_notes.append(
                f"RAG-suggested deadline (informational only, no dedicated field yet): {proposed['deadline_text']}"
            )
        links_patch["verification_notes"] = existing_notes
        top_level_updates["links"] = links_patch

    if top_level_updates:
        await update_scheme(db, scheme_id, SchemeUpdate.model_validate(top_level_updates))

    if "document_requirements" in proposed:
        scheme = await get_scheme(db, scheme_id)
        existing_types = {d["document_type"] for d in scheme.get("document_requirements", [])}
        merged = list(scheme.get("document_requirements", [])) + [
            {"document_type": doc_type, "is_mandatory": True}
            for doc_type in proposed["document_requirements"]
            if doc_type not in existing_types
        ]
        await update_scheme(db, scheme_id, SchemeUpdate(document_requirements=merged))

    await db.rag_candidate_updates.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"status": RagCandidateStatus.approved.value, "reviewed_at": now}},
    )
    return await get_candidate(db, candidate_id)


async def reject_candidate(db: AsyncIOMotorDatabase, candidate_id: str, reason: str | None) -> dict:
    candidate = await get_candidate(db, candidate_id)
    if candidate["status"] != RagCandidateStatus.pending.value:
        raise HTTPException(status_code=400, detail="Candidate update has already been reviewed")

    await db.rag_candidate_updates.update_one(
        {"_id": ObjectId(candidate_id)},
        {
            "$set": {
                "status": RagCandidateStatus.rejected.value,
                "reviewed_at": datetime.now(timezone.utc),
                "rejection_reason": reason,
            }
        },
    )
    return await get_candidate(db, candidate_id)
