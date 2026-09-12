from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.notification import NotificationOut
from app.modules.notifications import service

router = APIRouter(prefix="/api/citizens/{citizen_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.list_notifications(db, citizen_id)


@router.get("/unread-count")
async def get_unread_count(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return {"unread_count": await service.unread_count(db, citizen_id)}


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    citizen_id: str,
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.mark_read(db, citizen_id, notification_id)
