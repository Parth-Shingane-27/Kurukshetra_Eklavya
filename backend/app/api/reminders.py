from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.deadline_reminder import CreateReminderRequest, ReminderOut
from app.modules.deadline_reminder import service

router = APIRouter(prefix="/api/reminders", tags=["deadline-reminder"])


@router.post("", response_model=ReminderOut, status_code=201)
async def create_reminder(
    payload: CreateReminderRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, payload.citizen_id, current_user)
    return await service.create_reminder(db, payload.citizen_id, payload.scheme_id, payload.consent)


@router.get("/{citizen_id}", response_model=list[ReminderOut])
async def list_reminders(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.list_reminders_for_citizen(db, citizen_id)
