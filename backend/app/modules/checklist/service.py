from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.checklist.engine import build_checklist, compute_missing_documents
from app.modules.scheme_kb.service import get_schemes_by_ids
from app.rag.citations import attach_document_evidence

STEP_NAME = "checklist"


async def _load_bundle(db: AsyncIOMotorDatabase, bundle_id: str) -> dict:
    try:
        oid = ObjectId(bundle_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Bundle not found")
    doc = await db.bundles.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return doc


def _to_storage_items(items: list[dict]) -> list[dict]:
    return [{**item, "related_scheme_ids": [ObjectId(sid) for sid in item["related_scheme_ids"]]} for item in items]


def _to_response_items(items: list[dict]) -> list[dict]:
    return [{**item, "related_scheme_ids": [str(sid) for sid in item["related_scheme_ids"]]} for item in items]


async def generate_checklist(db: AsyncIOMotorDatabase, bundle_id: str) -> dict:
    bundle = await _load_bundle(db, bundle_id)
    citizen_id = str(bundle["citizen_id"])

    citizen = await db.citizens.find_one({"_id": bundle["citizen_id"]})
    if citizen is None:
        detail = "Profile not found"
        await log_step(db, citizen_id, STEP_NAME, {"bundle_id": bundle_id}, {"error": detail, "status_code": 404})
        raise HTTPException(status_code=404, detail=detail)

    bundle_schemes = await get_schemes_by_ids(db, bundle["scheme_ids"])
    held_documents = {d["document_type"] for d in citizen.get("documents", []) if d.get("held")}

    checklist_items = build_checklist(bundle_schemes, held_documents)
    # Best-effort RAG grounding (Section 6: Checklist Agent) — skipped when no GEMINI_API_KEY
    # is configured; items pass through unchanged in that case.
    checklist_items = await attach_document_evidence(checklist_items)
    missing_by_scheme = compute_missing_documents(bundle_schemes, held_documents)

    await db.bundles.update_one(
        {"_id": bundle["_id"]}, {"$set": {"checklist_items": _to_storage_items(checklist_items)}}
    )

    response = {
        "bundle_id": str(bundle["_id"]),
        "checklist_items": checklist_items,
        "missing_by_scheme": missing_by_scheme,
    }
    input_snapshot = {"bundle_id": bundle_id, "scheme_ids": [s["id"] for s in bundle_schemes]}
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response


async def get_checklist(db: AsyncIOMotorDatabase, bundle_id: str) -> dict:
    bundle = await _load_bundle(db, bundle_id)
    return {
        "bundle_id": str(bundle["_id"]),
        "checklist_items": _to_response_items(bundle.get("checklist_items", [])),
        "missing_by_scheme": None,
    }
