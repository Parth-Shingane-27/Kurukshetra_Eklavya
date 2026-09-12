"""LangGraph workflow for Context-Aware Form Assistance (browser extension / mobile toggle).

Deliberately a separate, smaller StateGraph from app/graph/workflow.py's general assistant
graph rather than another intent route on it: form assistance is entered through a signed
assistance session (see app/core/auth.py's `require_assistance_session`), never through free
text intent classification, and its output shape (FormAssistanceResponse) is purpose-built,
not a chat reply. Reuses the same building blocks the main graph already uses
(multilingual_service, get_policy_service()) rather than reimplementing them — same NFR-005
principle.

Node list (mirrors the requested design, adapted to what this codebase already provides):
extract_form_context -> detect_language -> identify_scheme_context -> retrieve_policy_evidence
-> generate_structured_explanation -> validate_grounding_and_finalize -> translate_output
`validate_assistance_session` itself is a FastAPI dependency (require_assistance_session), not
a graph node — this project's existing convention (get_current_user/require_admin) already
validates auth/session at the API layer, and duplicating that inside the graph would just be a
second, redundant check of the same JWT with no additional safety.
"""

import logging

from langchain_core.exceptions import ModelRateLimitError
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.graph.form_assistance_state import FormAssistanceState
from app.modules.assistance.schemas import FormExplanationDraft
from app.modules.multilingual import service as multilingual_service
from app.rag.policy_service import get_policy_service

logger = logging.getLogger(__name__)

_ELIGIBILITY_CAUTION = (
    "This explains what the field means. It is only one part of the eligibility assessment — "
    "your final eligibility may depend on other conditions evaluated together, not this field alone."
)


def _db(config) -> AsyncIOMotorDatabase:
    return config["configurable"]["db"]


def _consolidate(state: FormAssistanceState) -> str:
    parts = [
        state.get("field_label"),
        state.get("selected_text"),
        ", ".join(state.get("field_options") or []),
        state.get("nearby_help_text"),
    ]
    return "\n".join(p for p in parts if p)


_TRANSCRIBE_PROMPT = (
    "This image is a cropped screenshot of one small region of a government scheme "
    "application form. Transcribe ONLY the visible question/field label, any answer options "
    "shown (checkboxes, radio buttons, dropdown values), and any nearby help text — exactly as "
    "written. Do not answer the question, do not explain anything, do not describe the image's "
    "appearance or layout. If no readable form text is visible, respond with exactly: "
    "NO_READABLE_TEXT"
)

# Fail fast rather than the client default (6 retries with exponential backoff, which can turn
# a single rate-limited call into a 60s+ hang): one retry is enough to smooth over a transient
# blip, and anything past that should surface to the citizen quickly instead of stalling the
# whole assistance popup.
_LLM_MAX_RETRIES = 1

_RATE_LIMIT_ERROR = (
    "Our AI assistant has hit its usage limit for the moment — please try again in a few "
    "minutes, or select the form text directly instead."
)


async def _transcribe_screenshot(screenshot_base64: str, mime_type: str, settings) -> str | dict | None:
    """Vision-only transcription step for the screenshot-capture path (Section 7 Option B) —
    reuses the same Gemini model already used for explanation generation rather than adding a
    separate OCR dependency; the model both reads and (later, in a separate call) explains the
    text, matching how this codebase already treats Gemini as the one pluggable LLM service.
    Returns None (not a fabricated transcription) on an unreadable image, or a dict describing a
    genuine call failure (rate limit vs. anything else) so the caller can tell the citizen what
    actually happened instead of always blaming the screenshot.
    """
    if not settings.gemini_api_key:
        return None
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model, google_api_key=settings.gemini_api_key, max_retries=_LLM_MAX_RETRIES
        )
        message = HumanMessage(
            content=[
                {"type": "text", "text": _TRANSCRIBE_PROMPT},
                {"type": "image_url", "image_url": f"data:{mime_type};base64,{screenshot_base64}"},
            ]
        )
        result = await llm.ainvoke([message])
        text = (result.content or "").strip()
        if not text or text == "NO_READABLE_TEXT":
            return None
        return text
    except ModelRateLimitError:
        logger.warning("Screenshot transcription rate-limited.", exc_info=True)
        return {"error": _RATE_LIMIT_ERROR}
    except Exception as exc:
        logger.warning("Screenshot transcription failed (%s: %s); falling back to the no-context path.", type(exc).__name__, exc)
        return None


async def extract_form_context_node(state: FormAssistanceState, config) -> dict:
    text = _consolidate(state)
    if text.strip():
        return {"consolidated_text": text}

    if state.get("screenshot_base64"):
        settings = get_settings()
        transcribed = await _transcribe_screenshot(
            state["screenshot_base64"], state.get("screenshot_mime_type") or "image/png", settings
        )
        if isinstance(transcribed, dict):
            return {"errors": [transcribed["error"]]}
        if transcribed:
            return {"consolidated_text": transcribed}
        return {
            "errors": [
                "Could not read any form text in that screenshot — try selecting a clearer, "
                "smaller region, or select the text directly instead."
            ]
        }

    return {"errors": ["No form content was provided to explain (selected text, field label, help text, or a screenshot)."]}


async def detect_language_node(state: FormAssistanceState, config) -> dict:
    if not state.get("consolidated_text"):
        return {}
    settings = get_settings()
    result = await multilingual_service.detect_and_translate_to_english(
        state["consolidated_text"], settings.gemini_api_key, settings.gemini_model
    )
    return {"detected_language": result.detected_language, "translated_text": result.translated_text}


async def identify_scheme_context_node(state: FormAssistanceState, config) -> dict:
    db = _db(config)
    scheme = await db.schemes.find_one({"_id": _object_id(state["scheme_id"])})
    if scheme is None:
        return {"errors": ["The scheme associated with this assistance session no longer exists."]}
    scheme = dict(scheme)
    scheme["id"] = str(scheme.pop("_id"))
    return {"scheme": scheme}


def _object_id(scheme_id: str):
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        return ObjectId(scheme_id)
    except (InvalidId, TypeError):
        return ObjectId()  # a fresh, never-matching id — find_one returns None, handled above


async def retrieve_policy_evidence_node(state: FormAssistanceState, config) -> dict:
    if state.get("errors"):
        return {}
    query = state.get("translated_text") or state.get("consolidated_text") or ""
    result = await get_policy_service().retrieve_policy_evidence(
        query, filters={"scheme_id": state["scheme_id"]}, top_k=5
    )
    return {"policy_evidence": [e.model_dump() for e in result.evidence], "policy_verified": result.verified}


def _fallback_draft(state: FormAssistanceState) -> dict:
    """BR-010-style deterministic fallback — used when no Gemini key is configured or the LLM
    call fails, so the citizen always gets *something* rather than a 500."""
    label = state.get("field_label") or state.get("selected_text") or "This field"
    return FormExplanationDraft(
        question_meaning=f'"{label}" is a question on this scheme\'s application form.',
        what_information_is_expected=(
            "We could not generate a detailed explanation right now. Please read the form's "
            "own help text, or check the scheme's policy page for the exact requirement."
        ),
        needs_clarification=True,
        clarification_question="Could you share more of the surrounding form text so we can help further?",
        confidence=0.2,
    ).model_dump()


async def generate_structured_explanation_node(state: FormAssistanceState, config) -> dict:
    if state.get("errors"):
        return {}
    settings = get_settings()
    if not settings.gemini_api_key:
        return {"draft": _fallback_draft(state)}

    evidence_text = "\n".join(
        f"- {e['content']} (source: {e['source']}{', ' + e['source_url'] if e.get('source_url') else ''})"
        for e in (state.get("policy_evidence") or [])
    ) or "(no matching policy evidence was found for this scheme)"

    prompt = (
        "You are helping a citizen understand ONE question or option on a government scheme "
        "application form. You are NOT determining whether they are eligible for the scheme — "
        "that is a separate, deterministic process. Only explain what the field/question means, "
        "what each option (if any) means, what kind of information is expected, and a simple "
        "example if helpful. If the policy evidence below doesn't clearly cover this field, set "
        "needs_clarification=true and ask a specific clarification_question instead of guessing.\n\n"
        f"Scheme: {(state.get('scheme') or {}).get('name', 'Unknown scheme')}\n"
        f"Form content to explain:\n{state.get('translated_text') or state.get('consolidated_text')}\n\n"
        f"Relevant policy evidence:\n{evidence_text}\n"
    )
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model, google_api_key=settings.gemini_api_key, max_retries=_LLM_MAX_RETRIES
        )
        structured_llm = llm.with_structured_output(FormExplanationDraft)
        result = await structured_llm.ainvoke(prompt)
        draft = result if isinstance(result, FormExplanationDraft) else FormExplanationDraft.model_validate(result)
        return {"draft": draft.model_dump()}
    except ModelRateLimitError:
        logger.warning("Form-assistance explanation rate-limited; using deterministic fallback.", exc_info=True)
        draft = _fallback_draft(state)
        draft["what_information_is_expected"] = _RATE_LIMIT_ERROR
        return {"draft": draft}
    except Exception as exc:
        logger.warning(
            "Form-assistance explanation generation failed (%s: %s); using deterministic fallback.", type(exc).__name__, exc
        )
        return {"draft": _fallback_draft(state)}


async def validate_grounding_and_finalize_node(state: FormAssistanceState, config) -> dict:
    if state.get("errors"):
        return {}
    draft = dict(state.get("draft") or {})
    confidence = draft.get("confidence", 0.5)
    needs_clarification = draft.get("needs_clarification", False)

    if not state.get("policy_verified"):
        # No grounded policy evidence — never silently present a guess as scheme-specific.
        confidence = min(confidence, 0.4)
        needs_clarification = True
        draft["important_caution"] = (
            (draft.get("important_caution") + " " if draft.get("important_caution") else "")
            + "We could not confirm this against this scheme's specific policy text, so this "
            "is a general explanation only."
        ).strip()

    # BR-020: this sentence is enforced here, in code, every time — never left to the model's
    # own discretion to remember to include it.
    draft["important_caution"] = (
        (draft.get("important_caution") + " " if draft.get("important_caution") else "") + _ELIGIBILITY_CAUTION
    ).strip()

    policy_basis = [
        {"content": e["content"], "source": e["source"], "source_url": e.get("source_url")}
        for e in (state.get("policy_evidence") or [])
    ]

    final_response = {
        "detected_language": state.get("detected_language", "en"),
        "question_meaning": draft.get("question_meaning", ""),
        "option_explanations": draft.get("option_explanations", []),
        "what_information_is_expected": draft.get("what_information_is_expected", ""),
        "example": draft.get("example"),
        "important_caution": draft.get("important_caution"),
        "policy_basis": policy_basis,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "clarification_question": draft.get("clarification_question"),
    }
    return {"final_response": final_response}


async def translate_output_node(state: FormAssistanceState, config) -> dict:
    preferred = state.get("preferred_language")
    final_response = state.get("final_response")
    if state.get("errors") or not final_response or not preferred or preferred.lower() in ("en", "english"):
        return {}
    settings = get_settings()
    scheme_name = (state.get("scheme") or {}).get("name", "")
    fields_to_translate = ["question_meaning", "what_information_is_expected", "example", "important_caution"]
    updated = dict(final_response)
    any_warning = None
    for field in fields_to_translate:
        text = updated.get(field)
        if not text:
            continue
        result = await multilingual_service.translate_response(
            text, preferred, [scheme_name] if scheme_name else [], settings.gemini_api_key, settings.gemini_model
        )
        updated[field] = result["text"]
        if result["warning"]:
            any_warning = result["warning"]
    return {"final_response": updated, "warnings": [any_warning] if any_warning else []}


def build_form_assistance_graph():
    graph = StateGraph(FormAssistanceState)
    graph.add_node("extract_form_context", extract_form_context_node)
    graph.add_node("detect_language", detect_language_node)
    graph.add_node("identify_scheme_context", identify_scheme_context_node)
    graph.add_node("retrieve_policy_evidence", retrieve_policy_evidence_node)
    graph.add_node("generate_structured_explanation", generate_structured_explanation_node)
    graph.add_node("validate_grounding_and_finalize", validate_grounding_and_finalize_node)
    graph.add_node("translate_output", translate_output_node)

    graph.add_edge(START, "extract_form_context")
    graph.add_edge("extract_form_context", "detect_language")
    graph.add_edge("detect_language", "identify_scheme_context")
    graph.add_edge("identify_scheme_context", "retrieve_policy_evidence")
    graph.add_edge("retrieve_policy_evidence", "generate_structured_explanation")
    graph.add_edge("generate_structured_explanation", "validate_grounding_and_finalize")
    graph.add_edge("validate_grounding_and_finalize", "translate_output")
    graph.add_edge("translate_output", END)

    return graph.compile()


_compiled_form_assistance_graph = None


def get_form_assistance_graph():
    global _compiled_form_assistance_graph
    if _compiled_form_assistance_graph is None:
        _compiled_form_assistance_graph = build_form_assistance_graph()
    return _compiled_form_assistance_graph
