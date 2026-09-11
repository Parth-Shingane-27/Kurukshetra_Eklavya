from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.document_verification.engine import verify_document
from app.modules.profile.service import get_citizen
from app.rag.policy_service import PolicyKnowledgeService, get_policy_service
from app.services.document_parser import DocumentParseError, extract_text_from_base64_pdf

STEP_NAME = "document_verification"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc["citizen_id"] = str(doc["citizen_id"])
    return doc


async def verify_document_for_citizen(
    db: AsyncIOMotorDatabase,
    citizen_id: str,
    scheme_id: str,
    document_type: str,
    pdf_base64: str | None = None,
    document_text: str | None = None,
    declared_fields: dict | None = None,
    policy_service: PolicyKnowledgeService | None = None,
) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"
    declared_fields = declared_fields or {}

    extracted_text = document_text
    if pdf_base64:
        try:
            extracted_text = extract_text_from_base64_pdf(pdf_base64)
        except DocumentParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    service = policy_service or get_policy_service()
    retrieval = await service.retrieve_required_documents(scheme_id, db=db)
    required_texts = [e.content for e in retrieval.evidence]

    outcome = verify_document(document_type, required_texts, extracted_text, declared_fields)

    doc = {
        "citizen_id": ObjectId(citizen_id),
        "scheme_id": scheme_id,
        "document_type": document_type,
        "declared_fields": declared_fields,
        "extracted_text_present": bool((extracted_text or "").strip()),
        **outcome,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.document_verifications.insert_one(doc)
    created = await db.document_verifications.find_one({"_id": result.inserted_id})
    response = _serialize(created)

    input_snapshot = {
        "citizen_id": citizen_id, "scheme_id": scheme_id, "document_type": document_type,
        "declared_fields": declared_fields, "required_documents_found": len(required_texts),
    }
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response


async def get_document_verification(db: AsyncIOMotorDatabase, verification_id: str) -> dict:
    try:
        oid = ObjectId(verification_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Document verification not found")
    doc = await db.document_verifications.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Document verification not found")
    return _serialize(doc)


async def list_document_verifications_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> list[dict]:
    await get_citizen(db, citizen_id)  # raises 404
    cursor = db.document_verifications.find({"citizen_id": ObjectId(citizen_id)}).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]
