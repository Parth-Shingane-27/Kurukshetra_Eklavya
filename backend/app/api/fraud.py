from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.fraud_detection import FraudFlagOut, ReviewFraudFlagRequest, ScreenFraudRequest
from app.modules.fraud_detection import service

# Admin-only end to end: fraud screening is an internal trust-and-safety control, not a
# citizen-facing feature — a citizen seeing their own risk flags/indicators would defeat the
# purpose of a review mechanism meant to catch inconsistencies before a human looks at them.
router = APIRouter(prefix="/api/fraud", tags=["fraud-detection"], dependencies=[Depends(require_admin)])


@router.post("/screen", response_model=FraudFlagOut, status_code=201)
async def screen(payload: ScreenFraudRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.screen_citizen_for_fraud(db, payload.citizen_id, payload.scheme_id)


@router.get("", response_model=list[FraudFlagOut])
async def list_all_flags(
    risk_level: str | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.list_fraud_flags(db, risk_level=risk_level, reviewed=reviewed)


@router.get("/citizen/{citizen_id}", response_model=list[FraudFlagOut])
async def list_flags(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_fraud_flags_for_citizen(db, citizen_id)


@router.get("/{flag_id}", response_model=FraudFlagOut)
async def get_flag(flag_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_fraud_flag(db, flag_id)


@router.post("/{flag_id}/review", response_model=FraudFlagOut)
async def review_flag(flag_id: str, payload: ReviewFraudFlagRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.review_fraud_flag(db, flag_id, payload.reviewer_notes)
