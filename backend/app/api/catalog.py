from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.scheme import SchemeOut
from app.models.scheme_deadline import SchemeDeadlineOut
from app.modules.scheme_catalog import service
from app.modules.scheme_deadline import service as deadline_service

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/schemes", response_model=list[SchemeOut])
async def search_schemes(
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    state: str | None = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.search_catalog(db, query=query, category=category, state=state)


@router.get("/schemes/{scheme_id}/guide")
async def get_scheme_guide(scheme_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_scheme_guide(db, scheme_id)


@router.get("/schemes/{scheme_id}/deadline", response_model=SchemeDeadlineOut)
async def get_scheme_deadline(scheme_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await deadline_service.get_scheme_deadline(db, scheme_id)
