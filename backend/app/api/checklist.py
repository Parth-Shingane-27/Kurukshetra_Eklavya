from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.checklist import ChecklistResponse, GenerateChecklistRequest
from app.modules.checklist import service

router = APIRouter(prefix="/api/checklist", tags=["checklist"])


@router.post("/generate", response_model=ChecklistResponse)
async def generate(payload: GenerateChecklistRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.generate_checklist(db, payload.bundle_id)


@router.get("/{bundle_id}", response_model=ChecklistResponse)
async def get_checklist(bundle_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_checklist(db, bundle_id)
