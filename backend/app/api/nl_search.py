from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.nl_search import NLSearchRequest, NLSearchResponse
from app.modules.scheme_catalog import service

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.post("/search-natural-language", response_model=NLSearchResponse)
async def search_natural_language(payload: NLSearchRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.natural_language_search(db, payload.text)
