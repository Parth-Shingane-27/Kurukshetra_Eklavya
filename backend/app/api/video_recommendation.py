from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.video_recommendation import VideoRecommendationOut
from app.modules.video_recommendation import service

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/schemes/{scheme_id}/video-tutorial", response_model=VideoRecommendationOut)
async def get_video_tutorial(scheme_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_video_recommendation(db, scheme_id)
