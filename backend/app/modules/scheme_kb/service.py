import json
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.scheme import ConflictRuleCreate, SchemeCreate, SchemeUpdate

SEED_FILE = Path(__file__).resolve().parents[4] / "database" / "seed_schemes.json"


def _to_object_id(scheme_id: str) -> ObjectId:
    try:
        return ObjectId(scheme_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Scheme not found")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


async def list_schemes(
    db: AsyncIOMotorDatabase,
    category: str | None = None,
    state: str | None = None,
    include_inactive: bool = False,
) -> list[dict]:
    query: dict = {} if include_inactive else {"is_active": True}
    if category:
        query["category"] = category
    cursor = db.schemes.find(query).sort("_id", 1)
    schemes = [_serialize(doc) async for doc in cursor]

    if state:
        # Scheme has no top-level `state` field (Section 13); a state restriction is expressed
        # as a SchemeRule with field_name="state". Interpret the filter as: schemes with no
        # state-restricting rule (national schemes), or one whose state rule matches.
        def matches_state(scheme: dict) -> bool:
            state_rules = [r for r in scheme["rules"] if r["field_name"] == "state"]
            if not state_rules:
                return True
            return any(r["operator"] == "=" and r["value"] == state for r in state_rules)

        schemes = [s for s in schemes if matches_state(s)]

    return schemes


async def get_scheme(db: AsyncIOMotorDatabase, scheme_id: str) -> dict:
    oid = _to_object_id(scheme_id)
    doc = await db.schemes.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return _serialize(doc)


async def create_scheme(db: AsyncIOMotorDatabase, payload: SchemeCreate) -> dict:
    """FR-011: admin creates a scheme. Rule/document-requirement syntax is already validated
    by the SchemeCreate/SchemeRule pydantic models before this is ever called."""
    now = datetime.now(timezone.utc)
    doc = payload.model_dump(mode="json")
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db.schemes.insert_one(doc)
    created = await db.schemes.find_one({"_id": result.inserted_id})
    return _serialize(created)


async def update_scheme(db: AsyncIOMotorDatabase, scheme_id: str, payload: SchemeUpdate) -> dict:
    """FR-011: admin updates or deactivates (is_active=false) a scheme. Subsequent evaluations
    use the updated rules immediately — nothing caches the scheme catalogue."""
    oid = _to_object_id(scheme_id)
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if updates:
        # `links` is patched field-by-field via dot notation (e.g. "links.application_url")
        # rather than replacing the whole sub-document, so re-verifying one URL never
        # clobbers the other, unrelated link fields already stored on the scheme.
        links_patch = updates.pop("links", None)
        if links_patch:
            for key, value in links_patch.items():
                updates[f"links.{key}"] = value
        updates["updated_at"] = datetime.now(timezone.utc)
        result = await db.schemes.update_one({"_id": oid}, {"$set": updates})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Scheme not found")
    doc = await db.schemes.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return _serialize(doc)


async def get_schemes_by_ids(db: AsyncIOMotorDatabase, ids: list[ObjectId]) -> list[dict]:
    if not ids:
        return []
    cursor = db.schemes.find({"_id": {"$in": ids}})
    return [_serialize(doc) async for doc in cursor]


async def list_conflict_rules(db: AsyncIOMotorDatabase) -> list[dict]:
    """All declared conflict_rules (BR-004), with scheme id refs as strings for engine use."""
    cursor = db.conflict_rules.find({})
    return [
        {
            "scheme_a_id": str(doc["scheme_a_id"]),
            "scheme_b_id": str(doc["scheme_b_id"]),
            "conflict_type": doc["conflict_type"],
            "reason": doc.get("reason"),
        }
        async for doc in cursor
    ]


async def list_conflict_rules_detailed(db: AsyncIOMotorDatabase) -> list[dict]:
    """Admin-facing view of BR-004's declared conflict pairs, with scheme names resolved for
    display — distinct from list_conflict_rules(), which the Conflict Detection Engine uses
    internally and doesn't need names for.
    """
    cursor = db.conflict_rules.find({})
    rules = [doc async for doc in cursor]
    if not rules:
        return []
    scheme_ids = {doc["scheme_a_id"] for doc in rules} | {doc["scheme_b_id"] for doc in rules}
    schemes = await get_schemes_by_ids(db, list(scheme_ids))
    names_by_id = {s["id"]: s["name"] for s in schemes}
    return [
        {
            "id": str(doc["_id"]),
            "scheme_a_id": str(doc["scheme_a_id"]),
            "scheme_a_name": names_by_id.get(str(doc["scheme_a_id"]), "(unknown scheme)"),
            "scheme_b_id": str(doc["scheme_b_id"]),
            "scheme_b_name": names_by_id.get(str(doc["scheme_b_id"]), "(unknown scheme)"),
            "conflict_type": doc["conflict_type"],
            "reason": doc.get("reason"),
        }
        for doc in rules
    ]


async def create_conflict_rule(db: AsyncIOMotorDatabase, payload: ConflictRuleCreate) -> dict:
    """FR-011's conflict declaration (BR-004): admin declares two existing schemes as
    incompatible. Both schemes must exist — reuses get_scheme's 404 handling for that check."""
    await get_scheme(db, payload.scheme_a_id)
    await get_scheme(db, payload.scheme_b_id)
    doc = {
        "scheme_a_id": ObjectId(payload.scheme_a_id),
        "scheme_b_id": ObjectId(payload.scheme_b_id),
        "conflict_type": payload.conflict_type,
        "reason": payload.reason,
    }
    result = await db.conflict_rules.insert_one(doc)
    detailed = await list_conflict_rules_detailed(db)
    return next(r for r in detailed if r["id"] == str(result.inserted_id))


async def seed_schemes_if_empty(db: AsyncIOMotorDatabase) -> None:
    """Load database/seed_schemes.json on first run (dev/demo mode). No-op if already seeded."""
    if await db.schemes.count_documents({}) > 0:
        return

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)

    seed_key_to_id: dict[str, ObjectId] = {}
    for scheme in data["schemes"]:
        scheme = dict(scheme)
        seed_key = scheme.pop("seed_key")
        doc = {**scheme, "created_at": now, "updated_at": now}
        result = await db.schemes.insert_one(doc)
        seed_key_to_id[seed_key] = result.inserted_id

    for rule in data.get("conflict_rules", []):
        await db.conflict_rules.insert_one(
            {
                "scheme_a_id": seed_key_to_id[rule["scheme_a_key"]],
                "scheme_b_id": seed_key_to_id[rule["scheme_b_key"]],
                "conflict_type": rule["conflict_type"],
                "reason": rule.get("reason"),
            }
        )
