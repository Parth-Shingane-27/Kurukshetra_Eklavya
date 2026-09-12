from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.auth import RegisterRequest, TokenResponse, UserOut


def _serialize_user(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


async def register_user(db: AsyncIOMotorDatabase, payload: RegisterRequest) -> dict:
    settings = get_settings()
    email = payload.email.lower()

    if payload.role == "admin":
        if not payload.admin_bootstrap_credential or payload.admin_bootstrap_credential != settings.admin_credential:
            raise HTTPException(status_code=403, detail="Invalid admin bootstrap credential")

    existing = await db.users.find_one({"email": email})
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    now = datetime.now(timezone.utc)
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": payload.role.value if hasattr(payload.role, "value") else payload.role,
        "citizen_id": None,
        "created_at": now,
    }
    result = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": result.inserted_id})
    return _serialize_user(created)


async def _get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await db.users.find_one({"email": email.lower()})


async def _find_owned_citizen_id(db: AsyncIOMotorDatabase, user_id: str) -> str | None:
    """Covers citizen profiles created (via POST /api/citizens while logged in, which already
    stamps `owner_user_id`) before this account's `citizen_id` link existed — without this, a
    citizen who registered/logged in before their profile creation would never see their own
    dashboard after logging in again, since `users.citizen_id` would stay null forever."""
    citizen = await db.citizens.find_one({"owner_user_id": user_id}, sort=[("created_at", -1)])
    return str(citizen["_id"]) if citizen else None


async def login(db: AsyncIOMotorDatabase, email: str, password: str) -> TokenResponse:
    user = await _get_user_by_email(db, email)
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if user.get("citizen_id") is None:
        owned_citizen_id = await _find_owned_citizen_id(db, str(user["_id"]))
        if owned_citizen_id is not None:
            await link_citizen_to_user(db, str(user["_id"]), owned_citizen_id)
            user["citizen_id"] = owned_citizen_id

    access_token = create_access_token(user_id=str(user["_id"]), role=user["role"])
    return TokenResponse(access_token=access_token, user=UserOut(**_serialize_user(user)))


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    user = await db.users.find_one({"_id": oid})
    return _serialize_user(user) if user else None


async def link_citizen_to_user(db: AsyncIOMotorDatabase, user_id: str, citizen_id: str) -> None:
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"citizen_id": citizen_id}})
