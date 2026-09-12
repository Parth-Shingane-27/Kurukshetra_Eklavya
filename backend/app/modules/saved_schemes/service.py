from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.scheme_kb.service import get_scheme


def _serialize(doc: dict, scheme: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "citizen_id": str(doc["citizen_id"]),
        "scheme_id": str(doc["scheme_id"]),
        "scheme_name": scheme["name"],
        "scheme_category": scheme["category"],
        "saved_at": doc["saved_at"],
    }


async def save_scheme(db: AsyncIOMotorDatabase, citizen_id: str, scheme_id: str) -> dict:
    scheme = await get_scheme(db, scheme_id)  # 404s if the scheme doesn't exist
    try:
        citizen_oid = ObjectId(citizen_id)
        scheme_oid = ObjectId(scheme_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Profile not found")

    existing = await db.saved_schemes.find_one({"citizen_id": citizen_oid, "scheme_id": scheme_oid})
    if existing is not None:
        return _serialize(existing, scheme)

    doc = {"citizen_id": citizen_oid, "scheme_id": scheme_oid, "saved_at": datetime.now(timezone.utc)}
    result = await db.saved_schemes.insert_one(doc)
    created = await db.saved_schemes.find_one({"_id": result.inserted_id})
    return _serialize(created, scheme)


async def unsave_scheme(db: AsyncIOMotorDatabase, citizen_id: str, scheme_id: str) -> None:
    try:
        citizen_oid = ObjectId(citizen_id)
        scheme_oid = ObjectId(scheme_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Saved scheme not found")
    result = await db.saved_schemes.delete_one({"citizen_id": citizen_oid, "scheme_id": scheme_oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Saved scheme not found")


async def list_saved_schemes(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    try:
        citizen_oid = ObjectId(citizen_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Profile not found")

    cursor = db.saved_schemes.find({"citizen_id": citizen_oid}).sort("saved_at", -1)
    docs = [doc async for doc in cursor]
    if not docs:
        return []

    scheme_oids = {doc["scheme_id"] for doc in docs}
    schemes_by_id = {s["_id"]: s async for s in db.schemes.find({"_id": {"$in": list(scheme_oids)}})}

    results = []
    for doc in docs:
        scheme = schemes_by_id.get(doc["scheme_id"])
        if scheme is None:
            continue  # scheme was deleted since being saved — silently omit, don't 404 the whole list
        results.append(_serialize(doc, scheme))
    return results
