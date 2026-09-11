from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.feedback_grievance.engine import build_grievance_ticket
from app.modules.profile.service import get_citizen
from app.rag.policy_service import PolicyKnowledgeService, get_policy_service

STEP_NAME = "grievance"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    return doc


async def create_grievance(
    db: AsyncIOMotorDatabase,
    citizen_id: str,
    category: str,
    description: str,
    scheme_id: str | None = None,
    policy_service: PolicyKnowledgeService | None = None,
) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    department = None
    service = policy_service or get_policy_service()
    retrieval = await service.retrieve_grievance_procedure(scheme_id=scheme_id, db=db)
    if retrieval.evidence:
        department = retrieval.evidence[0].content

    ticket = build_grievance_ticket(category, description, scheme_id, department)

    doc = {
        "citizen_id": ObjectId(citizen_id),
        **ticket,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.grievances.insert_one(doc)
    created = await db.grievances.find_one({"_id": result.inserted_id})
    response = _serialize(created)

    input_snapshot = {"citizen_id": citizen_id, "scheme_id": scheme_id, "category": category}
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response


async def get_grievance(db: AsyncIOMotorDatabase, grievance_id: str) -> dict:
    try:
        oid = ObjectId(grievance_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Grievance not found")
    doc = await db.grievances.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Grievance not found")
    return _serialize(doc)


async def list_grievances_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    await get_citizen(db, citizen_id)  # raises 404
    cursor = db.grievances.find({"citizen_id": ObjectId(citizen_id)}).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]
