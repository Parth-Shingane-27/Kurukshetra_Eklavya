from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.citizen import CitizenCreate, CitizenOut, CitizenUpdate, DocumentsDeclare
from app.modules.profile import service

router = APIRouter(prefix="/api/citizens", tags=["citizens"])


@router.post("", response_model=CitizenOut, status_code=201)
async def create_citizen(payload: CitizenCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.create_citizen(db, payload)


@router.get("/{citizen_id}", response_model=CitizenOut)
async def get_citizen(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_citizen(db, citizen_id)


@router.put("/{citizen_id}", response_model=CitizenOut)
async def update_citizen(
    citizen_id: str, payload: CitizenUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.update_citizen(db, citizen_id, payload)


@router.post("/{citizen_id}/documents", response_model=CitizenOut)
async def declare_documents(
    citizen_id: str, payload: DocumentsDeclare, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.declare_documents(db, citizen_id, payload.documents)
