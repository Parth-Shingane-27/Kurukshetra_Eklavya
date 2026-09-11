from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.agent import RunPipelineRequest, RunPipelineResponse, TraceResponse
from app.modules.orchestrator import service

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/run", response_model=RunPipelineResponse)
async def run(payload: RunPipelineRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.run_pipeline(db, payload.citizen_id)


@router.get("/trace/{citizen_id}", response_model=TraceResponse)
async def get_trace(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_trace(db, citizen_id)
