from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.citizen import CitizenCreate, CitizenDocument, CitizenUpdate


def _to_object_id(citizen_id: str) -> ObjectId:
    try:
        return ObjectId(citizen_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Profile not found")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


async def create_citizen(db: AsyncIOMotorDatabase, payload: CitizenCreate) -> dict:
    now = datetime.now(timezone.utc)
    doc = payload.model_dump(mode="json")
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db.citizens.insert_one(doc)
    created = await db.citizens.find_one({"_id": result.inserted_id})
    return _serialize(created)


async def get_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    oid = _to_object_id(citizen_id)
    doc = await db.citizens.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(doc)


async def update_citizen(db: AsyncIOMotorDatabase, citizen_id: str, payload: CitizenUpdate) -> dict:
    oid = _to_object_id(citizen_id)
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        result = await db.citizens.update_one({"_id": oid}, {"$set": updates})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
        doc = await db.citizens.find_one({"_id": oid})
    else:
        doc = await db.citizens.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(doc)


async def declare_documents(
    db: AsyncIOMotorDatabase, citizen_id: str, documents: list[CitizenDocument]
) -> dict:
    oid = _to_object_id(citizen_id)
    result = await db.citizens.update_one(
        {"_id": oid},
        {
            "$set": {
                "documents": [d.model_dump() for d in documents],
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    doc = await db.citizens.find_one({"_id": oid})
    return _serialize(doc)
