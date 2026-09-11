from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import get_current_user_optional, require_assistance_session
from app.core.db import get_db
from app.graph.form_assistance_workflow import get_form_assistance_graph
from app.models.assistance import (
    AssistanceFeedbackRequest,
    AssistanceSessionOut,
    CreateAssistanceSessionRequest,
    FormAssistanceRequest,
    FormAssistanceResponse,
    ValidateSessionRequest,
    ValidateSessionResponse,
)
from app.modules.assistance import service

router = APIRouter(prefix="/api/assistance", tags=["assistance"])

# Whatever the Multi-language Chat Agent actually supports (app/modules/multilingual) — kept
# here rather than a longer hardcoded list, since claiming a language "works" when the
# underlying LLM/TTS stack doesn't handle it is exactly the dishonesty this feature must avoid.
SUPPORTED_LANGUAGES = [
    {"code": "en", "label": "English"},
    {"code": "hi", "label": "Hindi"},
    {"code": "mr", "label": "Marathi"},
]


@router.post("/session", response_model=AssistanceSessionOut)
async def create_session(
    payload: CreateAssistanceSessionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    return await service.create_session(db, payload.scheme_id, current_user)


@router.post("/validate-session", response_model=ValidateSessionResponse)
async def validate_session(payload: ValidateSessionRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.validate_session(db, payload.session_id, payload.origin)


@router.post("/explain-text", response_model=FormAssistanceResponse)
async def explain_text(
    payload: FormAssistanceRequest,
    session: dict = Depends(require_assistance_session),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    graph = get_form_assistance_graph()
    initial_state = {
        "scheme_id": session["scheme_id"],
        "selected_text": payload.selected_text,
        "field_label": payload.field_label,
        "field_options": payload.field_options,
        "nearby_help_text": payload.nearby_help_text,
        "preferred_language": payload.preferred_language,
        "errors": [],
        "warnings": [],
    }
    result = await graph.ainvoke(initial_state, config={"configurable": {"db": db}})
    if result.get("errors"):
        return FormAssistanceResponse(
            detected_language=result.get("detected_language", "en"),
            question_meaning="We couldn't generate an explanation for this.",
            what_information_is_expected="; ".join(result["errors"]),
            confidence=0.0,
            needs_clarification=True,
            clarification_question="Could you try selecting the specific question text again?",
        )
    return FormAssistanceResponse(**result["final_response"])


@router.get("/languages")
async def list_languages():
    return SUPPORTED_LANGUAGES


@router.post("/feedback")
async def submit_feedback(
    payload: AssistanceFeedbackRequest,
    session: dict = Depends(require_assistance_session),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.record_feedback(db, session["scheme_id"], session["allowed_origin"], payload.model_dump())
