from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.bundle import BundleOptimizeRequest, BundleOut
from app.modules.optimizer import service

router = APIRouter(prefix="/api/bundle", tags=["bundle"])


@router.post("/optimize", response_model=BundleOut)
async def optimize(
    payload: BundleOptimizeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, payload.citizen_id, current_user)
    return await service.optimize_bundle_for_citizen(db, payload.citizen_id)


@router.get("/{bundle_id}", response_model=BundleOut)
async def get_bundle(
    bundle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    result = await service.get_bundle(db, bundle_id)
    await check_owner_or_public(db, result["citizen_id"], current_user)
    return result
