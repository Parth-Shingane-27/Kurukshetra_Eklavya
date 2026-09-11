"""Single LangGraph entry point (Section 4 of the brief). Every existing per-stage REST
endpoint (eligibility/evaluate, bundle/optimize, etc.) remains untouched and keeps working
exactly as before — this is an additional, intent-routed surface on top of them, not a
replacement.
"""

from fastapi import APIRouter, Depends
from langgraph.types import Command
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.graph.workflow import get_compiled_graph
from app.models.assistant import AssistantMessageRequest, AssistantMessageResponse, AssistantResumeRequest

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

_STATE_KEYS = (
    "retrieved_policy_evidence", "eligibility_results", "conflicts_results", "bundle",
    "checklist", "document_verification_result", "deadline_info", "grievance_ticket",
    "fraud_risk_assessment", "language_context",
)


def _to_response(result: dict) -> AssistantMessageResponse:
    interrupted = "__interrupt__" in result
    return AssistantMessageResponse(
        detected_intent=result.get("detected_intent"),
        final_response=result.get("final_response") if not interrupted else None,
        human_review_required=bool(result.get("human_review_required")),
        interrupted=interrupted,
        errors=result.get("errors") or [],
        warnings=result.get("warnings") or [],
        state={k: result[k] for k in _STATE_KEYS if result.get(k) is not None},
    )


@router.post("/message", response_model=AssistantMessageResponse)
async def send_message(payload: AssistantMessageRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": payload.thread_id, "db": db}}
    initial_state = {
        "user_query": payload.user_query,
        "citizen_id": payload.citizen_id,
        "scheme_id": payload.scheme_id,
        "uploaded_document": payload.uploaded_document.model_dump() if payload.uploaded_document else None,
        "consent": payload.consent,
        "grievance_details": payload.grievance_details.model_dump() if payload.grievance_details else None,
        "errors": [],
        "warnings": [],
    }
    result = await graph.ainvoke(initial_state, config=config)
    return _to_response(result)


@router.post("/message/resume", response_model=AssistantMessageResponse)
async def resume_message(payload: AssistantResumeRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": payload.thread_id, "db": db}}
    result = await graph.ainvoke(Command(resume=payload.decision), config=config)
    return _to_response(result)
