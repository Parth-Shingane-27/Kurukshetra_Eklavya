"""Authentication dependencies.

FR-016 replaces the original prototype's single shared admin secret with real per-user
email+password+OTP accounts (see app/modules/auth). `require_admin` still accepts the legacy
`X-Admin-Token` header alongside a role=admin JWT — kept for backward compatibility with the
existing admin-token test suite and any deployment mid-migration; new admin sessions should use
the login flow. There was never a citizen-facing auth mechanism before (Q-002 was open); the new
`require_owner_or_public` dependency is additive: a citizen profile created without being logged
in (the original, still-supported anonymous/assisted-service flow) has no `owner_user_id` and
stays exactly as open as it always was, while a profile created by a logged-in citizen is now
genuinely protected.
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import decode_access_token, decode_assistance_token


def _decode_bearer(authorization: str | None) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return decode_access_token(token)


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    payload = _decode_bearer(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    user_id = payload.get("sub")
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    user = await db.users.find_one({"_id": oid})
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    user = dict(user)
    user["id"] = str(user.pop("_id"))
    return user


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict | None:
    payload = _decode_bearer(authorization)
    if payload is None:
        return None
    try:
        oid = ObjectId(payload.get("sub"))
    except (InvalidId, TypeError):
        return None
    user = await db.users.find_one({"_id": oid})
    if user is None:
        return None
    user = dict(user)
    user["id"] = str(user.pop("_id"))
    return user


async def require_admin(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    settings = get_settings()
    if x_admin_token and x_admin_token == settings.admin_credential:
        return

    payload = _decode_bearer(authorization)
    if payload is not None and payload.get("role") == "admin":
        try:
            oid = ObjectId(payload.get("sub"))
        except (InvalidId, TypeError):
            oid = None
        if oid is not None and await db.users.find_one({"_id": oid}) is not None:
            return

    raise HTTPException(status_code=401, detail="Invalid or missing admin credential")


async def check_owner_or_public(
    db: AsyncIOMotorDatabase, citizen_id: str, current_user: dict | None
) -> None:
    """Allows the request through when the target citizen record has no `owner_user_id`
    (legacy/anonymous profile — unchanged behavior), or when the caller is that profile's
    owner, or when the caller is an admin. Denies otherwise.

    Called directly from route handlers (rather than used as a bare `Depends`) since `citizen_id`
    arrives from different places across routes — a path parameter on the citizens.py routes,
    a request-body field on eligibility/conflicts/bundle/checklist/agent routes.
    """
    try:
        oid = ObjectId(citizen_id)
    except (InvalidId, TypeError):
        return  # let the route's own not-found handling report this
    citizen = await db.citizens.find_one({"_id": oid})
    if citizen is None:
        return  # let the route's own not-found handling report this
    owner_user_id = citizen.get("owner_user_id")
    if owner_user_id is None:
        return
    if current_user is not None and (
        current_user.get("role") == "admin" or current_user.get("id") == owner_user_id
    ):
        return
    raise HTTPException(status_code=403, detail="You do not have access to this profile")


async def require_assistance_session(
    authorization: str | None = Header(default=None),
    origin: str | None = Header(default=None, alias="X-Assistance-Origin"),
) -> dict:
    """Gates every `/api/assistance/explain-*` call. `scheme_id`/`allowed_origin` come ONLY
    from the signed `assistance_token` (never a client-supplied body field — see
    FormAssistanceRequest's docstring) and the caller's actual origin must match what the
    token was issued for, using the same header the browser itself sets (not spoofable by
    page JS) — a stolen/replayed token from a different site still can't be used from that
    site, only from the origin it was scoped to at `/assistance/validate-session` time.
    """
    payload = None
    if authorization and authorization.lower().startswith("bearer "):
        payload = decode_assistance_token(authorization.split(" ", 1)[1].strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing or invalid assistance session")
    if not origin or origin != payload.get("allowed_origin"):
        raise HTTPException(status_code=403, detail="This origin is not authorized for this assistance session")
    return {"scheme_id": payload["scheme_id"], "allowed_origin": payload["allowed_origin"]}


async def citizen_id_for_bundle(db: AsyncIOMotorDatabase, bundle_id: str) -> str | None:
    """Looks up the owning citizen_id for a bundle_id, for routes (checklist.py) that only
    receive a bundle_id, not a citizen_id — so `check_owner_or_public` still has something to
    check against. Returns None (rather than raising) on a bad/missing id; the route's own
    service call still reports the real 404 for that case.
    """
    try:
        oid = ObjectId(bundle_id)
    except (InvalidId, TypeError):
        return None
    bundle = await db.bundles.find_one({"_id": oid}, {"citizen_id": 1})
    return str(bundle["citizen_id"]) if bundle else None
