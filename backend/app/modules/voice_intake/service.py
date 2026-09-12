"""FR-012 — Multilingual Conversational & Voice Profile Intake.

Architectural boundary (A-008): this module's ONLY job is filling the same FR-001 `Citizen`
profile schema, one slot at a time, plus one clarifying follow-up question — never open-ended
chat, never answering questions about scheme policy. BR-013's guarantee (every extracted value
passes the identical validation a structured-form submission would) is enforced by literally
reusing `CitizenUpdate`/`CitizenCreate` to validate extracted values and `profile.service.
create_citizen` to persist the finished profile — there is no second, parallel validator or
persistence path for conversational intake.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError

from app.core.config import get_settings
from app.models.citizen import CitizenCreate, CitizenUpdate
from app.models.voice_intake import ExtractedProfileSlots, SlotExtractionDraft
from app.modules.multilingual.service import detect_and_translate_to_english, translate_response
from app.modules.profile import service as profile_service

logger = logging.getLogger(__name__)

MANDATORY_FIELDS = ["name", "date_of_birth", "state", "district"]
KNOWN_FIELDS = list(ExtractedProfileSlots.model_fields)

_FIELD_PROMPTS_EN = {
    "name": "What is your full name?",
    "date_of_birth": "What is your date of birth?",
    "state": "Which state do you live in?",
    "district": "Which district do you live in?",
}

_STRUCTURED_FORM_FALLBACK_MESSAGE = (
    "We're having trouble understanding right now. Please continue using the structured form "
    "instead so you don't get stuck."
)


def _next_missing_mandatory_field(collected: dict) -> str | None:
    for field in MANDATORY_FIELDS:
        if collected.get(field) in (None, ""):
            return field
    return None


def _default_next_question(collected: dict) -> str:
    field = _next_missing_mandatory_field(collected)
    if field is None:
        return "Thanks — I have everything needed to check your eligible schemes."
    return _FIELD_PROMPTS_EN[field]


def _format_validation_error(exc: ValidationError) -> str:
    return "; ".join(e["msg"] for e in exc.errors())


async def _get_or_create_session(db: AsyncIOMotorDatabase, session_id: str | None) -> dict:
    if session_id:
        existing = await db.intake_sessions.find_one({"session_id": session_id})
        if existing is not None:
            return existing
    new_session_id = session_id or secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": new_session_id,
        "collected_profile": {},
        "submitted_citizen_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.intake_sessions.insert_one(doc)
    return doc


async def _save_session(db: AsyncIOMotorDatabase, session: dict) -> None:
    session["updated_at"] = datetime.now(timezone.utc)
    await db.intake_sessions.update_one(
        {"session_id": session["session_id"]},
        {
            "$set": {
                "collected_profile": session["collected_profile"],
                "submitted_citizen_id": session.get("submitted_citizen_id"),
                "updated_at": session["updated_at"],
            }
        },
    )


def _build_extraction_prompt(english_transcript: str, collected: dict) -> str:
    known_so_far = ", ".join(f"{k}={v}" for k, v in collected.items()) or "(nothing yet)"
    return (
        "You are filling out a government benefits profile form ONE FIELD AT A TIME through "
        "conversation. You are NOT answering questions about scheme eligibility or policy — "
        "only extracting profile facts the citizen states, and asking one clarifying question "
        "for whichever mandatory field is still missing. Only extract a field if the citizen's "
        f"message clearly states it. Known so far: {known_so_far}.\n\n"
        f"Citizen's message (already translated to English): {english_transcript}\n\n"
        "Mandatory fields still needed, in priority order: name, date_of_birth (as YYYY-MM-DD), "
        "state, district. Other optional fields: gender, annual_income, occupation, "
        "social_category, disability_status, land_holding_acres, family_size, marital_status, "
        "bpl_status, education_level, employment_status."
    )


async def _extract_slots(english_transcript: str, collected: dict, settings) -> SlotExtractionDraft | None:
    try:
        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        structured_llm = llm.with_structured_output(SlotExtractionDraft)
        result = await structured_llm.ainvoke(_build_extraction_prompt(english_transcript, collected))
        return result if isinstance(result, SlotExtractionDraft) else SlotExtractionDraft.model_validate(result)
    except Exception:
        logger.warning("Conversational intake slot extraction failed; falling back to a structured question.", exc_info=True)
        return None


async def converse(
    db: AsyncIOMotorDatabase, transcript: str, session_id: str | None, target_language: str | None, owner_user_id: str | None
) -> dict:
    settings = get_settings()
    session = await _get_or_create_session(db, session_id)
    collected: dict[str, Any] = dict(session["collected_profile"])
    rejected: dict[str, str] = {}

    detected = await detect_and_translate_to_english(transcript, settings.gemini_api_key, settings.gemini_model)
    reply_language = target_language or detected.detected_language

    if session.get("submitted_citizen_id"):
        message_en = "Your profile is already complete — you can head to your eligible schemes."
    elif not settings.gemini_api_key:
        message_en = _STRUCTURED_FORM_FALLBACK_MESSAGE
    else:
        draft = await _extract_slots(detected.translated_text, collected, settings)
        if draft is None:
            fallback_field = _next_missing_mandatory_field(collected)
            message_en = (
                f"Let's try that as a quick question instead: {_FIELD_PROMPTS_EN[fallback_field]}"
                if fallback_field
                else _STRUCTURED_FORM_FALLBACK_MESSAGE
            )
        else:
            for field, raw_value in draft.extracted.model_dump(exclude_none=True).items():
                if field not in KNOWN_FIELDS:
                    continue
                try:
                    validated = CitizenUpdate.model_validate({field: raw_value})
                except ValidationError as exc:
                    rejected[field] = _format_validation_error(exc)
                    continue
                # JSON-safe form (e.g. date -> ISO string) — this dict is persisted to Mongo
                # and also fed straight into CitizenCreate at completion, which parses the ISO
                # string back into a real `date` exactly as the structured form's own JSON body
                # would (BR-013).
                collected[field] = validated.model_dump(mode="json", exclude_unset=True)[field]
            message_en = draft.follow_up_question_en or _default_next_question(collected)

    citizen_id = session.get("submitted_citizen_id")
    is_complete = _next_missing_mandatory_field(collected) is None

    if is_complete and citizen_id is None:
        try:
            citizen_payload = CitizenCreate.model_validate(collected)
        except ValidationError:
            is_complete = False
        else:
            created = await profile_service.create_citizen(db, citizen_payload, owner_user_id=owner_user_id)
            citizen_id = created["id"]

    session["collected_profile"] = collected
    session["submitted_citizen_id"] = citizen_id
    await _save_session(db, session)

    translation = await translate_response(
        message_en, reply_language, critical_values=[], api_key=settings.gemini_api_key, model=settings.gemini_model
    )

    return {
        "session_id": session["session_id"],
        "detected_language": detected.detected_language,
        "collected_profile": collected,
        "rejected_fields": rejected,
        "assistant_message": translation["text"],
        "is_complete": is_complete,
        "citizen_id": citizen_id,
    }
