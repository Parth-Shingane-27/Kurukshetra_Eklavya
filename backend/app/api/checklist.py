from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, citizen_id_for_bundle, get_current_user_optional
from app.core.db import get_db
from app.models.checklist import ChecklistResponse, GenerateChecklistRequest
from app.modules.checklist import service

router = APIRouter(prefix="/api/checklist", tags=["checklist"])


@router.post("/generate", response_model=ChecklistResponse)
async def generate(
    payload: GenerateChecklistRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    citizen_id = await citizen_id_for_bundle(db, payload.bundle_id)
    if citizen_id is not None:
        await check_owner_or_public(db, citizen_id, current_user)
    return await service.generate_checklist(db, payload.bundle_id)


@router.get("/{bundle_id}", response_model=ChecklistResponse)
async def get_checklist(
    bundle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    citizen_id = await citizen_id_for_bundle(db, bundle_id)
    if citizen_id is not None:
        await check_owner_or_public(db, citizen_id, current_user)
    return await service.get_checklist(db, bundle_id)
