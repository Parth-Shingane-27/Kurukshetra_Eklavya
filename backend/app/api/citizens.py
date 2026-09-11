from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.citizen import CitizenCreate, CitizenOut, CitizenUpdate, DocumentsDeclare
from app.modules.profile import service

router = APIRouter(prefix="/api/citizens", tags=["citizens"])


@router.post("", response_model=CitizenOut, status_code=201)
async def create_citizen(
    payload: CitizenCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    owner_user_id = current_user["id"] if current_user else None
    return await service.create_citizen(db, payload, owner_user_id=owner_user_id)


@router.get("/{citizen_id}", response_model=CitizenOut)
async def get_citizen(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.get_citizen(db, citizen_id)


@router.put("/{citizen_id}", response_model=CitizenOut)
async def update_citizen(
    citizen_id: str,
    payload: CitizenUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.update_citizen(db, citizen_id, payload)


@router.post("/{citizen_id}/documents", response_model=CitizenOut)
async def declare_documents(
    citizen_id: str,
    payload: DocumentsDeclare,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.declare_documents(db, citizen_id, payload.documents)
