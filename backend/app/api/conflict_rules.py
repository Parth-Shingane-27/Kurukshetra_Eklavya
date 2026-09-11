from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.scheme import ConflictRuleCreate, ConflictRuleOut
from app.modules.scheme_kb import service

router = APIRouter(prefix="/api/conflict-rules", tags=["conflict-rules"])


@router.get("", response_model=list[ConflictRuleOut])
async def list_conflict_rules(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_conflict_rules_detailed(db)


@router.post("", response_model=ConflictRuleOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_conflict_rule(payload: ConflictRuleCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.create_conflict_rule(db, payload)
