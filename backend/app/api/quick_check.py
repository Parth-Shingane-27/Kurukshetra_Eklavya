from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.quick_check import QuickCheckRequest, QuickCheckResponse
from app.modules.quick_checker import service

router = APIRouter(prefix="/api/quick-check", tags=["quick-check"])


@router.post("", response_model=QuickCheckResponse)
async def quick_check(payload: QuickCheckRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.quick_check(db, payload.scheme_id, payload.criteria)
