from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.deadline_reminder.engine import ConsentRequiredError, build_reminder_record
from app.modules.profile.service import get_citizen
from app.rag.policy_service import PolicyKnowledgeService, get_policy_service

STEP_NAME = "deadline_reminder"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    return doc


async def create_reminder(
    db: AsyncIOMotorDatabase,
    citizen_id: str,
    scheme_id: str,
    consent: bool,
    policy_service: PolicyKnowledgeService | None = None,
) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    service = policy_service or get_policy_service()
    retrieval = await service.retrieve_deadlines(scheme_id, db=db)
    deadline_text = retrieval.evidence[0].content if retrieval.evidence else None

    try:
        record = build_reminder_record(
            citizen_id, scheme_id, consent,
            deadline_verified=retrieval.verified, deadline_text=deadline_text,
        )
    except ConsentRequiredError as exc:
        await log_step(
            db, citizen_id, STEP_NAME, {"citizen_id": citizen_id, "scheme_id": scheme_id},
            {"error": str(exc), "status_code": 422},
        )
        raise HTTPException(status_code=422, detail=str(exc))

    doc = {
        "citizen_id": ObjectId(citizen_id),
        "scheme_id": scheme_id,
        **record,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.reminders.insert_one(doc)
    created = await db.reminders.find_one({"_id": result.inserted_id})
    response = _serialize(created)

    input_snapshot = {"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": consent}
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response


async def list_reminders_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    await get_citizen(db, citizen_id)  # raises 404
    cursor = db.reminders.find({"citizen_id": ObjectId(citizen_id)}).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]
