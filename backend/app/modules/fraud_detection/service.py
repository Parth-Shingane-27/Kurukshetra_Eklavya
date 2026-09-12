from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.core.config import get_settings
from app.modules.fraud_detection.engine import screen_for_fraud_risk
from app.modules.fraud_detection.summary import generate_fraud_summary
from app.modules.profile.service import get_citizen

STEP_NAME = "fraud_detection"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    return doc


async def screen_citizen_for_fraud(
    db: AsyncIOMotorDatabase, citizen_id: str, scheme_id: str | None = None
) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    query: dict = {"citizen_id": ObjectId(citizen_id)}
    if scheme_id:
        query["scheme_id"] = scheme_id
    verifications = [_serialize(doc) async for doc in db.document_verifications.find(query)]

    screening = screen_for_fraud_risk(verifications)
    settings = get_settings()
    summary = await generate_fraud_summary(screening, settings.gemini_api_key, settings.gemini_model)

    doc = {
        "citizen_id": ObjectId(citizen_id),
        "scheme_id": scheme_id,
        "risk_level": screening["risk_level"],
        "indicators": screening["indicators"],
        "human_review_required": screening["human_review_required"],
        "summary": summary,
        "reviewed": False,
        "reviewer_notes": None,
        "reviewed_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.fraud_flags.insert_one(doc)
    created = await db.fraud_flags.find_one({"_id": result.inserted_id})
    response = _serialize(created)

    input_snapshot = {
        "citizen_id": citizen_id, "scheme_id": scheme_id, "verifications_screened": len(verifications),
    }
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response


async def get_fraud_flag(db: AsyncIOMotorDatabase, flag_id: str) -> dict:
    try:
        oid = ObjectId(flag_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Fraud flag not found")
    doc = await db.fraud_flags.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Fraud flag not found")
    return _serialize(doc)


async def list_fraud_flags_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    await get_citizen(db, citizen_id)  # raises 404
    cursor = db.fraud_flags.find({"citizen_id": ObjectId(citizen_id)}).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def list_fraud_flags(
    db: AsyncIOMotorDatabase, risk_level: str | None = None, reviewed: bool | None = None
) -> list[dict]:
    """Admin-only review queue across every citizen's fraud flags."""
    query: dict = {}
    if risk_level:
        query["risk_level"] = risk_level
    if reviewed is not None:
        query["reviewed"] = reviewed
    cursor = db.fraud_flags.find(query).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def review_fraud_flag(db: AsyncIOMotorDatabase, flag_id: str, reviewer_notes: str) -> dict:
    try:
        oid = ObjectId(flag_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Fraud flag not found")
    doc = await db.fraud_flags.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Fraud flag not found")
    if doc.get("reviewed"):
        raise HTTPException(status_code=400, detail="Fraud flag has already been reviewed")

    now = datetime.now(timezone.utc)
    await db.fraud_flags.update_one(
        {"_id": oid},
        {"$set": {"reviewed": True, "reviewer_notes": reviewer_notes, "reviewed_at": now}},
    )
    updated = await db.fraud_flags.find_one({"_id": oid})
    return _serialize(updated)
