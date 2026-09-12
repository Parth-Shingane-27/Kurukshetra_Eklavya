from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import get_current_user_optional
from app.core.db import get_db
from app.models.voice_intake import ConverseRequest, ConverseResponse
from app.modules.voice_intake import service

router = APIRouter(prefix="/api/intake", tags=["voice-intake"])


@router.post("/converse", response_model=ConverseResponse)
async def converse(
    payload: ConverseRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    owner_user_id = current_user["id"] if current_user else None
    return await service.converse(
        db,
        transcript=payload.transcript,
        session_id=payload.session_id,
        target_language=payload.target_language,
        owner_user_id=owner_user_id,
    )
