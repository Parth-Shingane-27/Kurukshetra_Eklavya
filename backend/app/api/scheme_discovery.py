from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.scheme_discovery import (
    SchemeDiscoveryOut,
    SchemeDiscoveryRejectRequest,
    SchemeDiscoverySearchRequest,
)
from app.modules.scheme_discovery import service

router = APIRouter(prefix="/api/admin", tags=["scheme-discovery"], dependencies=[Depends(require_admin)])


@router.post("/scheme-discovery/search", response_model=list[SchemeDiscoveryOut])
async def search_schemes(payload: SchemeDiscoverySearchRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.discover_schemes(db, payload.query, category=payload.category)


@router.get("/scheme-discoveries", response_model=list[SchemeDiscoveryOut])
async def list_discoveries(status: str | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_discoveries(db, status=status)


@router.get("/scheme-discoveries/{discovery_id}", response_model=SchemeDiscoveryOut)
async def get_discovery(discovery_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_discovery(db, discovery_id)


@router.post("/scheme-discoveries/{discovery_id}/approve", response_model=SchemeDiscoveryOut)
async def approve_discovery(discovery_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.approve_discovery(db, discovery_id)


@router.post("/scheme-discoveries/{discovery_id}/reject", response_model=SchemeDiscoveryOut)
async def reject_discovery(
    discovery_id: str, payload: SchemeDiscoveryRejectRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.reject_discovery(db, discovery_id, reason=payload.reason)
