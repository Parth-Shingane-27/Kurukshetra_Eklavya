from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.conflict_engine.engine import detect_conflicts
from app.modules.explanation.service import generate_explanation
from app.modules.optimizer.engine import optimize_bundle
from app.modules.profile.service import get_citizen
from app.modules.rule_engine.service import get_latest_eligible_schemes
from app.modules.scheme_kb.service import list_conflict_rules

STEP_NAME = "bundle_optimization"
EXPLANATION_STEP_NAME = "explanation"


def _serialize_bundle(doc: dict) -> dict:
    doc = dict(doc)
    doc["bundle_id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    doc["scheme_ids"] = [str(sid) for sid in doc["scheme_ids"]]
    doc["excluded"] = [
        {**e, "scheme_id": str(e["scheme_id"])} for e in doc.pop("excluded_schemes", [])
    ]
    doc.pop("checklist_items", None)
    return doc


async def optimize_bundle_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    try:
        eligible_schemes = await get_latest_eligible_schemes(db, citizen_id)  # raises 422
    except HTTPException as exc:
        await log_step(
            db, citizen_id, STEP_NAME, {"citizen_id": citizen_id}, {"error": exc.detail, "status_code": exc.status_code}
        )
        raise

    conflict_rules = await list_conflict_rules(db)

    conflicts = detect_conflicts(eligible_schemes, conflict_rules)
    result = optimize_bundle(eligible_schemes, conflicts)

    id_to_scheme = {s["id"]: s for s in eligible_schemes}
    included = [
        {
            "scheme_id": sid,
            "scheme_name": id_to_scheme[sid]["name"],
            "benefit_value_estimate": id_to_scheme[sid]["benefit_value_estimate"],
        }
        for sid in result["scheme_ids"]
    ]
    # FR-007: explanation generation is embedded in this same call, not a separate endpoint.
    explanation_text = await generate_explanation(
        {
            "total_benefit_value": result["total_benefit_value"],
            "included": included,
            "excluded": result["excluded"],
        }
    )

    doc = {
        "citizen_id": ObjectId(citizen_id),
        "scheme_ids": [ObjectId(sid) for sid in result["scheme_ids"]],
        "total_benefit_value": result["total_benefit_value"],
        "excluded_schemes": [
            {
                "scheme_id": ObjectId(e["scheme_id"]),
                "scheme_name": e["scheme_name"],
                "reason": e["reason"],
            }
            for e in result["excluded"]
        ],
        "explanation_text": explanation_text,
        "checklist_items": [],
        "generated_at": datetime.now(timezone.utc),
    }
    insert_result = await db.bundles.insert_one(doc)
    created = await db.bundles.find_one({"_id": insert_result.inserted_id})
    serialized = _serialize_bundle(created)

    input_snapshot = {
        "citizen_id": citizen_id,
        "eligible_scheme_ids": [s["id"] for s in eligible_schemes],
        "conflicts": conflicts,
    }
    await log_step(
        db, citizen_id, STEP_NAME, input_snapshot, {k: v for k, v in serialized.items() if k != "explanation_text"}
    )
    # FR-010 names explanation as a distinct pipeline stage even though it's computed above,
    # inside this same call, per FR-007's traceability note.
    await log_step(
        db,
        citizen_id,
        EXPLANATION_STEP_NAME,
        {
            "bundle_id": serialized["bundle_id"],
            "included_scheme_ids": serialized["scheme_ids"],
            "excluded": serialized["excluded"],
        },
        {"explanation_text": explanation_text},
    )
    return serialized


async def get_bundle(db: AsyncIOMotorDatabase, bundle_id: str) -> dict:
    try:
        oid = ObjectId(bundle_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Bundle not found")
    doc = await db.bundles.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return _serialize_bundle(doc)
