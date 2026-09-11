"""Session handshake for Context-Aware Form Assistance — see app/models/assistance.py's
module docstring for the two-step design this implements.
"""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.security import create_assistance_token
from app.modules.scheme_kb.service import get_scheme

# Statuses a citizen may still be offered assistance for — `not_available`/`state_specific`
# never get a session at all, since there is no verified (or even attempted) online
# application destination to attach assistance to.
_ASSISTABLE_STATUSES = {"verified", "unverified"}


def _origin_of(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def create_session(db: AsyncIOMotorDatabase, scheme_id: str, current_user: dict | None) -> dict:
    scheme = await get_scheme(db, scheme_id)
    links = scheme.get("links") or {}
    application_url = links.get("application_url")
    status = links.get("application_link_status")

    if not application_url or status not in _ASSISTABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                "This scheme has no online application link to assist with "
                f"(status: {status or 'not_available'})."
            ),
        )

    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.assistance_session_expire_seconds)
    session_id = secrets.token_urlsafe(24)

    await db.assistance_sessions.insert_one(
        {
            "session_id": session_id,
            "scheme_id": scheme_id,
            "scheme_name": scheme["name"],
            "allowed_origin": _origin_of(application_url),
            "application_link_status": status,
            "user_id": current_user["id"] if current_user else None,
            "created_at": now,
            "expires_at": expires_at,
        }
    )
    return {
        "session_id": session_id,
        "application_url": application_url,
        "application_link_status": status,
        "expires_at": expires_at,
    }


async def validate_session(db: AsyncIOMotorDatabase, session_id: str, origin: str) -> dict:
    doc = await db.assistance_sessions.find_one({"session_id": session_id})
    if doc is None:
        return {"valid": False, "reason": "This assistance session is unknown or has already expired."}

    expires_at = doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        return {"valid": False, "reason": "This assistance session has expired. Reopen the scheme from our platform."}

    if origin != doc["allowed_origin"]:
        return {
            "valid": False,
            "reason": "This page is not the verified application destination for this scheme.",
        }

    token = create_assistance_token(scheme_id=doc["scheme_id"], allowed_origin=origin)
    settings = get_settings()
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.assistance_token_expire_seconds)
    return {
        "valid": True,
        "scheme_id": doc["scheme_id"],
        "scheme_name": doc["scheme_name"],
        "assistance_token": token,
        "expires_at": token_expires_at,
    }


async def record_feedback(db: AsyncIOMotorDatabase, scheme_id: str, allowed_origin: str, payload: dict) -> dict:
    """Stored for a curator to review — never fed back into the explanation prompt
    automatically, since unvetted feedback text is exactly the kind of unreviewed input BR-015
    already establishes must never reach a live, decision-relevant record."""
    now = datetime.now(timezone.utc)
    doc = {**payload, "scheme_id": scheme_id, "allowed_origin": allowed_origin, "created_at": now}
    result = await db.assistance_feedback.insert_one(doc)
    return {"feedback_id": str(result.inserted_id)}
