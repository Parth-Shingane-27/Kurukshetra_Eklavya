from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.bundle import BundleOptimizeRequest, BundleOut
from app.modules.optimizer import service

router = APIRouter(prefix="/api/bundle", tags=["bundle"])


@router.post("/optimize", response_model=BundleOut)
async def optimize(payload: BundleOptimizeRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.optimize_bundle_for_citizen(db, payload.citizen_id)


@router.get("/{bundle_id}", response_model=BundleOut)
async def get_bundle(bundle_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_bundle(db, bundle_id)
