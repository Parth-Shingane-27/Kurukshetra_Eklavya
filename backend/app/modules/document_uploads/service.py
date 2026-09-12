"""Plain document management for a citizen's own reference — see the module docstring in
app/models/document_upload.py for why this is deliberately NOT verification.
"""

import base64
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.citizen import CitizenDocument
from app.models.document_upload import DocumentUploadCreate


def _to_object_id(upload_id: str) -> ObjectId:
    try:
        return ObjectId(upload_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Document not found")


def _serialize_meta(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "citizen_id": doc["citizen_id"],
        "document_type": doc["document_type"],
        "filename": doc["filename"],
        "content_type": doc["content_type"],
        "size_bytes": doc["size_bytes"],
        "uploaded_at": doc["uploaded_at"],
    }


async def _mark_document_held(db: AsyncIOMotorDatabase, citizen_oid: ObjectId, document_type: str) -> None:
    """Auto-marks the matching `CitizenDocument.held = True` on the profile so the
    missing-document checklist reflects an uploaded document without a separate manual
    declaration step. Adds a new entry if this document_type wasn't previously declared at
    all."""
    citizen = await db.citizens.find_one({"_id": citizen_oid})
    if citizen is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    documents = citizen.get("documents", [])
    found = False
    for d in documents:
        if d["document_type"] == document_type:
            d["held"] = True
            found = True
            break
    if not found:
        documents.append(CitizenDocument(document_type=document_type, held=True).model_dump())
    await db.citizens.update_one(
        {"_id": citizen_oid},
        {"$set": {"documents": documents, "updated_at": datetime.now(timezone.utc)}},
    )


async def upload_document(db: AsyncIOMotorDatabase, citizen_id: str, payload: DocumentUploadCreate) -> dict:
    try:
        citizen_oid = ObjectId(citizen_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Profile not found")

    decoded = base64.b64decode(payload.file_base64, validate=True)
    now = datetime.now(timezone.utc)
    doc = {
        "citizen_id": citizen_id,
        "document_type": payload.document_type,
        "filename": payload.filename,
        "content_type": payload.content_type,
        "file_bytes": decoded,
        "size_bytes": len(decoded),
        "uploaded_at": now,
    }
    result = await db.document_uploads.insert_one(doc)
    await _mark_document_held(db, citizen_oid, payload.document_type)
    created = await db.document_uploads.find_one({"_id": result.inserted_id})
    return _serialize_meta(created)


async def list_documents(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    cursor = db.document_uploads.find({"citizen_id": citizen_id}).sort("uploaded_at", -1)
    return [_serialize_meta(doc) async for doc in cursor]


async def get_document_content(db: AsyncIOMotorDatabase, citizen_id: str, upload_id: str) -> dict:
    oid = _to_object_id(upload_id)
    doc = await db.document_uploads.find_one({"_id": oid, "citizen_id": citizen_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc["_id"]),
        "filename": doc["filename"],
        "content_type": doc["content_type"],
        "file_base64": base64.b64encode(doc["file_bytes"]).decode("ascii"),
    }


async def delete_document(db: AsyncIOMotorDatabase, citizen_id: str, upload_id: str) -> None:
    oid = _to_object_id(upload_id)
    result = await db.document_uploads.delete_one({"_id": oid, "citizen_id": citizen_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
