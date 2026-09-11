from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import log_step
from app.modules.conflict_engine.engine import detect_conflicts
from app.modules.profile.service import get_citizen
from app.modules.rule_engine.service import get_latest_eligible_schemes
from app.modules.scheme_kb.service import list_conflict_rules

STEP_NAME = "conflicts"


async def detect_conflicts_for_citizen(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    try:
        eligible_schemes = await get_latest_eligible_schemes(db, citizen_id)  # raises 422
    except HTTPException as exc:
        await log_step(
            db, citizen_id, STEP_NAME, {"citizen_id": citizen_id}, {"error": exc.detail, "status_code": exc.status_code}
        )
        raise

    conflict_rules = await list_conflict_rules(db)
    conflicts = detect_conflicts(eligible_schemes, conflict_rules)
    response = {"citizen_id": citizen_id, "conflicts": conflicts}

    input_snapshot = {"citizen_id": citizen_id, "eligible_scheme_ids": [s["id"] for s in eligible_schemes]}
    await log_step(db, citizen_id, STEP_NAME, input_snapshot, response)
    return response
