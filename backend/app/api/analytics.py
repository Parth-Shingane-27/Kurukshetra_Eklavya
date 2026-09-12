from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.analytics import AnalyticsOut
from app.modules.analytics import service

router = APIRouter(prefix="/api/admin/analytics", tags=["analytics"], dependencies=[Depends(require_admin)])


@router.get("", response_model=AnalyticsOut)
async def get_analytics(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_platform_analytics(db)
