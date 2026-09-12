from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.feedback_grievance.engine import build_grievance_ticket
from app.modules.notifications.service import create_notification
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
    await create_notification(
        db, citizen_id, "grievance_created",
        f"Your ticket {response['ticket_id']} was submitted and is now open.",
        related_id=response["id"],
    )
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


async def list_grievances(db: AsyncIOMotorDatabase, status: str | None = None) -> list[dict]:
    """Admin-facing: every grievance across all citizens, for the review queue."""
    query = {"status": status} if status else {}
    cursor = db.grievances.find(query).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def resolve_grievance(db: AsyncIOMotorDatabase, grievance_id: str, resolution_note: str) -> dict:
    try:
        oid = ObjectId(grievance_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Grievance not found")
    doc = await db.grievances.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Grievance not found")
    if doc["status"] == "resolved":
        raise HTTPException(status_code=400, detail="Grievance has already been resolved")

    now = datetime.now(timezone.utc)
    await db.grievances.update_one(
        {"_id": oid},
        {"$set": {"status": "resolved", "resolution_note": resolution_note, "resolved_at": now}},
    )
    updated = await db.grievances.find_one({"_id": oid})
    response = _serialize(updated)
    await create_notification(
        db, response["citizen_id"], "grievance_resolved",
        f"Your ticket {response['ticket_id']} was resolved: {resolution_note}",
        related_id=response["id"],
    )
    return response
