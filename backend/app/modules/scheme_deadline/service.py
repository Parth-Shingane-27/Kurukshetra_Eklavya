"""Public, citizen-independent scheme deadline lookup for the scheme catalog/browse views —
distinct from app.modules.deadline_reminder, which persists a citizen-specific reminder record
and is gated behind explicit consent (it stores personal data: citizen_id + scheme_id
together). This module only ever surfaces the same underlying
policy_service.retrieve_deadlines() text as read-only informational content on a scheme card,
for any visitor, cached per-scheme (not per-citizen) the same way
app.modules.video_recommendation caches YouTube lookups — so browsing the catalog doesn't
re-run RAG retrieval on every page view.
"""

from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.modules.scheme_kb.service import get_scheme
from app.rag.policy_service import get_policy_service


def _to_out(doc: dict, cached: bool) -> dict:
    return {
        "scheme_id": doc["scheme_id"],
        "available": doc["available"],
        "deadline_text": doc.get("deadline_text"),
        "reason": doc.get("reason"),
        "last_checked_at": doc["last_checked_at"],
        "cached": cached,
    }


async def get_scheme_deadline(db: AsyncIOMotorDatabase, scheme_id: str) -> dict:
    await get_scheme(db, scheme_id)  # 404s if the scheme itself doesn't exist
    settings = get_settings()

    cached = await db.scheme_deadline_cache.find_one({"scheme_id": scheme_id})
    if cached is not None:
        last_checked_at = cached["last_checked_at"]
        if last_checked_at.tzinfo is None:
            last_checked_at = last_checked_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_checked_at
        if age < timedelta(days=settings.scheme_deadline_cache_ttl_days):
            return _to_out(cached, cached=True)

    policy_service = get_policy_service()
    retrieval = await policy_service.retrieve_deadlines(scheme_id, db=db)
    now = datetime.now(timezone.utc)
    doc = {
        "scheme_id": scheme_id,
        "available": bool(retrieval.verified and retrieval.evidence),
        "deadline_text": retrieval.evidence[0].content if retrieval.evidence else None,
        "reason": None if retrieval.verified else (retrieval.note or "No verified deadline on file for this scheme yet."),
        "last_checked_at": now,
    }
    await db.scheme_deadline_cache.update_one({"scheme_id": scheme_id}, {"$set": doc}, upsert=True)
    return _to_out(doc, cached=False)
