from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.scheme import SchemeCreate, SchemeOut, SchemeUpdate
from app.modules.scheme_kb import service

router = APIRouter(prefix="/api/schemes", tags=["schemes"])


@router.get("", response_model=list[SchemeOut])
async def list_schemes(
    category: str | None = Query(default=None),
    state: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.list_schemes(db, category=category, state=state, include_inactive=include_inactive)


@router.get("/{scheme_id}", response_model=SchemeOut)
async def get_scheme(scheme_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_scheme(db, scheme_id)


@router.post("", response_model=SchemeOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_scheme(payload: SchemeCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.create_scheme(db, payload)


@router.put("/{scheme_id}", response_model=SchemeOut, dependencies=[Depends(require_admin)])
async def update_scheme(
    scheme_id: str, payload: SchemeUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.update_scheme(db, scheme_id, payload)
