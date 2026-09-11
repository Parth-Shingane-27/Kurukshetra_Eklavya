from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.bundle import ConflictDetectRequest, ConflictDetectResponse
from app.modules.conflict_engine import service

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


@router.post("/detect", response_model=ConflictDetectResponse)
async def detect(payload: ConflictDetectRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.detect_conflicts_for_citizen(db, payload.citizen_id)
