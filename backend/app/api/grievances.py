from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.feedback_grievance import CreateGrievanceRequest, GrievanceOut
from app.modules.feedback_grievance import service

router = APIRouter(prefix="/api/grievances", tags=["feedback-grievance"])


@router.post("", response_model=GrievanceOut, status_code=201)
async def create_grievance(payload: CreateGrievanceRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.create_grievance(
        db, payload.citizen_id, payload.category, payload.description, payload.scheme_id
    )


@router.get("/citizen/{citizen_id}", response_model=list[GrievanceOut])
async def list_grievances(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_grievances_for_citizen(db, citizen_id)


@router.get("/{grievance_id}", response_model=GrievanceOut)
async def get_grievance(grievance_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_grievance(db, grievance_id)
