"""Shared audit-log helper (BR-012). Lives in app/core rather than the orchestrator module so
every stage service (rule_engine, conflict_engine, optimizer, checklist) can log itself directly
when invoked — whether called individually via its own endpoint or sequenced by the Agent
Orchestrator — without those lower modules depending on the orchestrator (which depends on them).
"""

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def log_step(
    db: AsyncIOMotorDatabase,
    citizen_id: str,
    step_name: str,
    input_snapshot: dict,
    output_snapshot: dict,
) -> None:
    await db.agent_audit_logs.insert_one(
        {
            "citizen_id": ObjectId(citizen_id),
            "step_name": step_name,
            "input_snapshot": input_snapshot,
            "output_snapshot": output_snapshot,
            "created_at": datetime.now(timezone.utc),
        }
    )
