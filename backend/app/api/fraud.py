from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.fraud_detection import FraudFlagOut, ScreenFraudRequest
from app.modules.fraud_detection import service

router = APIRouter(prefix="/api/fraud", tags=["fraud-detection"])


@router.post("/screen", response_model=FraudFlagOut, status_code=201)
async def screen(payload: ScreenFraudRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.screen_citizen_for_fraud(db, payload.citizen_id, payload.scheme_id)


@router.get("/citizen/{citizen_id}", response_model=list[FraudFlagOut])
async def list_flags(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_fraud_flags_for_citizen(db, citizen_id)


@router.get("/{flag_id}", response_model=FraudFlagOut)
async def get_flag(flag_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_fraud_flag(db, flag_id)
