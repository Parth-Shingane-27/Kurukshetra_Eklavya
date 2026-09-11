from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.eligibility import EvaluateRequest, EvaluateResponse
from app.modules.rule_engine import service

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(payload: EvaluateRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.evaluate_eligibility(db, payload.citizen_id)
