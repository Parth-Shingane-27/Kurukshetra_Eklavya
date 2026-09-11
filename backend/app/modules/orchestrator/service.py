"""Agent Orchestrator (FR-010, BR-012). Sequences the existing, independently-tested stage
services in order — eligibility -> conflicts -> optimization (+ explanation, embedded per
FR-007) -> checklist. Each stage service logs its own agent_audit_logs entry (see
app.core.audit), so the trace is populated whether a stage is reached through this one-shot
endpoint or by calling that stage's own endpoint directly — this orchestrator adds pure
sequencing/convenience on top, not a second logging path.

Deliberately reuses each stage's existing service function rather than reimplementing any
eligibility/conflict/optimization logic here (NFR-005 — no rule logic duplicated/hardcoded
outside the data-driven modules that already own it).
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.checklist.service import generate_checklist
from app.modules.conflict_engine.service import detect_conflicts_for_citizen
from app.modules.optimizer.service import optimize_bundle_for_citizen
from app.modules.profile.service import get_citizen
from app.modules.rule_engine.service import evaluate_eligibility


async def run_pipeline(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"

    eligibility_result = await evaluate_eligibility(db, citizen_id)
    conflicts_result = await detect_conflicts_for_citizen(db, citizen_id)
    bundle_result = await optimize_bundle_for_citizen(db, citizen_id)
    checklist_result = await generate_checklist(db, bundle_result["bundle_id"])

    return {
        "citizen_id": citizen_id,
        "eligibility": eligibility_result,
        "conflicts": conflicts_result,
        "bundle": bundle_result,
        "checklist": checklist_result,
    }


async def get_trace(db: AsyncIOMotorDatabase, citizen_id: str) -> dict:
    await get_citizen(db, citizen_id)  # raises 404 "Profile not found"
    oid = ObjectId(citizen_id)
    cursor = db.agent_audit_logs.find({"citizen_id": oid}).sort("created_at", 1)
    steps = [
        {
            "step_name": doc["step_name"],
            "input_snapshot": doc["input_snapshot"],
            "output_snapshot": doc["output_snapshot"],
            "created_at": doc["created_at"],
        }
        async for doc in cursor
    ]
    return {"citizen_id": citizen_id, "steps": steps}
