from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.saved_scheme import SavedSchemeOut, SaveSchemeRequest
from app.modules.saved_schemes import service

router = APIRouter(prefix="/api/citizens/{citizen_id}/saved-schemes", tags=["saved-schemes"])


@router.post("", response_model=SavedSchemeOut, status_code=201)
async def save_scheme(
    citizen_id: str,
    payload: SaveSchemeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.save_scheme(db, citizen_id, payload.scheme_id)


@router.get("", response_model=list[SavedSchemeOut])
async def list_saved_schemes(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.list_saved_schemes(db, citizen_id)


@router.delete("/{scheme_id}", status_code=204)
async def unsave_scheme(
    citizen_id: str,
    scheme_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    await service.unsave_scheme(db, citizen_id, scheme_id)
