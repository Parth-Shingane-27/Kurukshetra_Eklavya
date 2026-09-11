from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.profile.service import get_citizen
from app.modules.rule_engine.engine import build_profile_context, evaluate_scheme
from app.modules.scheme_kb.service import get_schemes_by_ids, list_schemes

STEP_NAME = "eligibility"


async def evaluate_eligibility(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    citizen = await get_citizen(db, citizen_id)  # raises 404 "Profile not found"
    schemes = await list_schemes(db)  # active schemes only (BR-003)

    profile_context = build_profile_context(citizen)
    evaluated_at = datetime.now(timezone.utc)

    results = []
    docs_to_insert = []
    for scheme in schemes:
        outcome = evaluate_scheme(scheme, profile_context)
        results.append(
            {
                "scheme_id": scheme["id"],
                "scheme_name": scheme["name"],
                "status": outcome["status"],
                "reasons": outcome["reasons"],
            }
        )
        docs_to_insert.append(
            {
                "citizen_id": ObjectId(citizen_id),
                "scheme_id": ObjectId(scheme["id"]),
                "status": outcome["status"],
                "reasons": outcome["reasons"],
                "evaluated_at": evaluated_at,
            }
        )

    if docs_to_insert:
        await db.eligibility_results.insert_many(docs_to_insert)

    if results and all(r["status"] == "indeterminate" for r in results):
        detail = "Profile is missing fields required by every active scheme; nothing could be evaluated."
        await log_step(db, citizen_id, STEP_NAME, citizen, {"error": detail, "status_code": 409})
        raise HTTPException(status_code=409, detail=detail)

    response = {"citizen_id": citizen_id, "evaluated_at": evaluated_at, "results": results}
    await log_step(db, citizen_id, STEP_NAME, citizen, response)
    return response


async def get_latest_eligible_schemes(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    """Scheme dicts that were 'eligible' in the citizen's most recent evaluation run.

    Assumes the caller has already validated the citizen exists (404). Raises 422 if
    eligibility has never been evaluated for this citizen (Section 15/21's documented case
    for the endpoints that depend on this — conflicts/detect, bundle/optimize).
    """
    oid = ObjectId(citizen_id)
    latest = await db.eligibility_results.find_one({"citizen_id": oid}, sort=[("evaluated_at", -1)])
    if latest is None:
        raise HTTPException(status_code=422, detail="Run eligibility evaluation first")

    cursor = db.eligibility_results.find(
        {"citizen_id": oid, "evaluated_at": latest["evaluated_at"], "status": "eligible"}
    )
    eligible_scheme_object_ids = [doc["scheme_id"] async for doc in cursor]
    return await get_schemes_by_ids(db, eligible_scheme_object_ids)
