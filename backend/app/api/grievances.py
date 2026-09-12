from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional, require_admin
from app.core.db import get_db
from app.models.feedback_grievance import CreateGrievanceRequest, GrievanceOut, ResolveGrievanceRequest
from app.modules.feedback_grievance import service

router = APIRouter(prefix="/api/grievances", tags=["feedback-grievance"])


@router.post("", response_model=GrievanceOut, status_code=201)
async def create_grievance(
    payload: CreateGrievanceRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, payload.citizen_id, current_user)
    return await service.create_grievance(
        db, payload.citizen_id, payload.category, payload.description, payload.scheme_id
    )


@router.get("", response_model=list[GrievanceOut], dependencies=[Depends(require_admin)])
async def list_all_grievances(status: str | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Admin-only review queue across every citizen's grievances."""
    return await service.list_grievances(db, status=status)


@router.get("/citizen/{citizen_id}", response_model=list[GrievanceOut])
async def list_grievances(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.list_grievances_for_citizen(db, citizen_id)


@router.get("/{grievance_id}", response_model=GrievanceOut)
async def get_grievance(
    grievance_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    grievance = await service.get_grievance(db, grievance_id)
    await check_owner_or_public(db, grievance["citizen_id"], current_user)
    return grievance


@router.post("/{grievance_id}/resolve", response_model=GrievanceOut, dependencies=[Depends(require_admin)])
async def resolve_grievance(
    grievance_id: str, payload: ResolveGrievanceRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.resolve_grievance(db, grievance_id, payload.resolution_note)
