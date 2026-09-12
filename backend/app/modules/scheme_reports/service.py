from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.scheme_kb.service import get_scheme


def _serialize(doc: dict, scheme_name: str) -> dict:
    return {
        "id": str(doc["_id"]),
        "scheme_id": str(doc["scheme_id"]),
        "scheme_name": scheme_name,
        "reason": doc["reason"],
        "comment": doc.get("comment"),
        "citizen_id": str(doc["citizen_id"]) if doc.get("citizen_id") else None,
        "status": doc["status"],
        "admin_notes": doc.get("admin_notes"),
        "resolved_at": doc.get("resolved_at"),
        "created_at": doc["created_at"],
    }


async def create_report(
    db: AsyncIOMotorDatabase, scheme_id: str, reason: str, comment: str | None, citizen_id: str | None
) -> dict:
    scheme = await get_scheme(db, scheme_id)  # 404s if the scheme doesn't exist
    doc = {
        "scheme_id": ObjectId(scheme_id),
        "reason": reason,
        "comment": comment,
        "citizen_id": ObjectId(citizen_id) if citizen_id else None,
        "status": "open",
        "admin_notes": None,
        "resolved_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.scheme_reports.insert_one(doc)
    created = await db.scheme_reports.find_one({"_id": result.inserted_id})
    return _serialize(created, scheme["name"])


async def list_reports(db: AsyncIOMotorDatabase, status: str | None = None) -> list[dict]:
    query = {"status": status} if status else {}
    cursor = db.scheme_reports.find(query).sort("created_at", -1)
    docs = [doc async for doc in cursor]
    if not docs:
        return []
    scheme_oids = {doc["scheme_id"] for doc in docs}
    schemes_by_id = {s["_id"]: s async for s in db.schemes.find({"_id": {"$in": list(scheme_oids)}})}
    return [
        _serialize(doc, schemes_by_id[doc["scheme_id"]]["name"] if doc["scheme_id"] in schemes_by_id else "(deleted scheme)")
        for doc in docs
    ]


async def resolve_report(db: AsyncIOMotorDatabase, report_id: str, status: str, admin_notes: str | None) -> dict:
    try:
        oid = ObjectId(report_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Report not found")
    doc = await db.scheme_reports.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if doc["status"] != "open":
        raise HTTPException(status_code=400, detail="Report has already been resolved")

    now = datetime.now(timezone.utc)
    await db.scheme_reports.update_one(
        {"_id": oid}, {"$set": {"status": status, "admin_notes": admin_notes, "resolved_at": now}}
    )
    updated = await db.scheme_reports.find_one({"_id": oid})
    scheme = await db.schemes.find_one({"_id": updated["scheme_id"]})
    scheme_name = scheme["name"] if scheme else "(deleted scheme)"
    return _serialize(updated, scheme_name)
