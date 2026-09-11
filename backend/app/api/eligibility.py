from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.eligibility import EvaluateRequest, EvaluateResponse
from app.modules.rule_engine import service

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    payload: EvaluateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, payload.citizen_id, current_user)
    return await service.evaluate_eligibility(db, payload.citizen_id)
