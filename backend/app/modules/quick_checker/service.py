"""FR-013 — Quick Scheme Eligibility Checker. Stateless (BR-014): nothing about this request
is ever written to Mongo — no citizen record, no eligibility_results row, no audit log entry.
Reuses the Rule Engine's own `evaluate_scheme`/`build_profile_context` (app/modules/
rule_engine/engine.py) rather than a second eligibility implementation.
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.rule_engine.engine import build_profile_context, evaluate_scheme

MAX_ALTERNATIVES = 3


def _to_object_id(scheme_id: str) -> ObjectId:
    try:
        return ObjectId(scheme_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Scheme not found")


async def quick_check(db: AsyncIOMotorDatabase, scheme_id: str, criteria: dict) -> dict:
    oid = _to_object_id(scheme_id)
    scheme = await db.schemes.find_one({"_id": oid, "is_active": True})
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # A convenience, not a second intake path: if the caller supplied date_of_birth instead of
    # age directly, derive age the identical way FR-001's structured form/BR-001 already do —
    # never a separately-defined age calculation.
    profile_context = build_profile_context(criteria) if "date_of_birth" in criteria else dict(criteria)

    outcome = evaluate_scheme(scheme, profile_context)

    links = scheme.get("links") or {}
    response = {
        "scheme_id": scheme_id,
        "scheme_name": scheme["name"],
        "status": outcome["status"],
        "reasons": outcome["reasons"],
        "application_url": links.get("application_url"),
        "application_link_status": links.get("application_link_status"),
        "official_scheme_url": links.get("official_scheme_url"),
        "required_documents": [d["document_type"] for d in scheme.get("document_requirements", [])],
        "suggested_alternatives": [],
    }

    if outcome["status"] == "not_eligible":
        cursor = db.schemes.find(
            {"category": scheme["category"], "is_active": True, "_id": {"$ne": oid}}
        ).limit(MAX_ALTERNATIVES)
        response["suggested_alternatives"] = [
            {"scheme_id": str(doc["_id"]), "scheme_name": doc["name"]} async for doc in cursor
        ]

    return response
