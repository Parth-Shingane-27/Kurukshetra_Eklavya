from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.web_scheme_search import WebSchemeSearchResponse
from app.modules.profile.service import get_citizen
from app.modules.web_scheme_search import service

router = APIRouter(prefix="/api/citizens/{citizen_id}/web-schemes", tags=["web-scheme-search"])


@router.get("", response_model=WebSchemeSearchResponse)
async def get_web_schemes(
    citizen_id: str,
    force: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    citizen = await get_citizen(db, citizen_id)
    return await service.get_personalized_web_schemes(db, citizen, force=force)
