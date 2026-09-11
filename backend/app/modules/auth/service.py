from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.email_sender import send_otp_email
from app.core.security import (
    create_access_token,
    generate_otp_code,
    generate_pending_token,
    hash_otp_code,
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


async def login_step1(db: AsyncIOMotorDatabase, email: str, password: str) -> tuple[str, str | None]:
    """Verifies email+password (step 1) and emails an OTP (step 2 setup).

    Returns (pending_token, debug_otp). debug_otp is None unless email delivery fell back to
    console logging (see app/core/email_sender.py).
    """
    settings = get_settings()
    user = await _get_user_by_email(db, email)
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    code = generate_otp_code()
    pending_token = generate_pending_token()
    now = datetime.now(timezone.utc)
    await db.pending_logins.insert_one(
        {
            "pending_token": pending_token,
            "user_id": user["_id"],
            "code_hash": hash_otp_code(code),
            "attempts": 0,
            "created_at": now,
            "expires_at": now + timedelta(seconds=settings.otp_expire_seconds),
        }
    )

    sent_via_resend = await send_otp_email(to_email=user["email"], code=code)
    debug_otp = None if sent_via_resend else code
    return pending_token, debug_otp


async def verify_otp(db: AsyncIOMotorDatabase, pending_token: str, code: str) -> TokenResponse:
    settings = get_settings()
    pending = await db.pending_logins.find_one({"pending_token": pending_token})
    if pending is None:
        raise HTTPException(status_code=401, detail="Invalid or expired verification session")

    now = datetime.now(timezone.utc)
    expires_at = pending["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        await db.pending_logins.delete_one({"_id": pending["_id"]})
        raise HTTPException(status_code=401, detail="Verification code expired, please log in again")

    if pending["attempts"] >= settings.otp_max_attempts:
        await db.pending_logins.delete_one({"_id": pending["_id"]})
        raise HTTPException(status_code=401, detail="Too many incorrect attempts, please log in again")

    if hash_otp_code(code) != pending["code_hash"]:
        await db.pending_logins.update_one({"_id": pending["_id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=401, detail="Incorrect verification code")

    await db.pending_logins.delete_one({"_id": pending["_id"]})

    user = await db.users.find_one({"_id": pending["user_id"]})
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")

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
