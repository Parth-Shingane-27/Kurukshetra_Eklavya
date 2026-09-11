from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.bundle import ConflictDetectRequest, ConflictDetectResponse
from app.modules.conflict_engine import service

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


@router.post("/detect", response_model=ConflictDetectResponse)
async def detect(
    payload: ConflictDetectRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, payload.citizen_id, current_user)
    return await service.detect_conflicts_for_citizen(db, payload.citizen_id)
