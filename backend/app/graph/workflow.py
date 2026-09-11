"""Top-level LangGraph workflow (Section 8/9 of the brief).

Nodes are thin adapters over the existing agent service functions — both the original 8
(rule_engine, conflict_engine, optimizer, checklist) and the 5 new ones — never a
reimplementation of their logic (same NFR-005 principle the existing Agent Orchestrator
already follows, in app/modules/orchestrator/service.py). A node catches `HTTPException`
from its underlying service and writes to `state["errors"]` instead of letting it propagate,
since nodes run inside LangGraph's runtime, not inside a FastAPI request/exception-handling
context.

Subgraphs (Section 9) are expressed here as conditional-edge node *sequences* within one
StateGraph rather than nested compiled subgraphs — at this project's scale that's an
equivalent, simpler mechanism for "don't force every request through every node" (Section 8),
and it keeps one visible graph definition instead of splitting it across files for no
functional benefit.

`db` is threaded through via `config["configurable"]["db"]` rather than graph state, since a
Motor database handle isn't checkpoint-serializable (see state.py's docstring).
"""

from fastapi import HTTPException
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.graph.routing import detect_intent
from app.graph.state import AgentState
from app.modules.checklist import service as checklist_service
from app.modules.conflict_engine import service as conflict_engine_service
from app.modules.deadline_reminder import service as deadline_reminder_service
from app.modules.document_verification import service as document_verification_service
from app.modules.feedback_grievance import service as feedback_grievance_service
from app.modules.fraud_detection import service as fraud_detection_service
from app.modules.multilingual import service as multilingual_service
from app.modules.optimizer import service as optimizer_service
from app.modules.rule_engine import service as rule_engine_service
from app.rag.policy_service import get_policy_service


def _db(config) -> AsyncIOMotorDatabase:
    return config["configurable"]["db"]


def _http_error(exc: HTTPException) -> str:
    return f"{exc.status_code}: {exc.detail}"


# --- Language handling (Section 7.4) ---------------------------------------------------

async def language_in_node(state: AgentState, config) -> dict:
    settings = get_settings()
    result = await multilingual_service.detect_and_translate_to_english(
        state["user_query"], settings.gemini_api_key, settings.gemini_model
    )
    return {
        "translated_query": result.translated_text,
        "language_context": {"detected_language": result.detected_language, "target_language": result.detected_language},
    }


async def language_out_node(state: AgentState, config) -> dict:
    settings = get_settings()
    language_context = state.get("language_context") or {}
    target_language = language_context.get("target_language", "en")
    if target_language.lower() == "en" or not state.get("final_response"):
        return {}

    critical_values: list[str] = []
    bundle = state.get("bundle")
    if bundle:
        critical_values.extend(s["scheme_name"] for s in bundle.get("policy_citations") or [])
        critical_values.append(str(bundle.get("total_benefit_value", "")))
    for evidence in state.get("retrieved_policy_evidence") or []:
        critical_values.append(evidence["scheme_name"])

    result = await multilingual_service.translate_response(
        state["final_response"], target_language, critical_values,
        settings.gemini_api_key, settings.gemini_model,
    )
    update: dict = {"final_response": result["text"]}
    if result["warning"]:
        update["warnings"] = [result["warning"]]
    return update


# --- Intent routing ----------------------------------------------------------------------

async def intent_node(state: AgentState, config) -> dict:
    query = state.get("translated_query") or state["user_query"]
    return {"detected_intent": detect_intent(query)}


def route_by_intent(state: AgentState) -> str:
    return state.get("detected_intent", "GENERAL_QUERY")


# --- Scheme recommendation (Section 9's first subgraph) -----------------------------------

async def scheme_recommendation_node(state: AgentState, config) -> dict:
    citizen_id = state.get("citizen_id")
    if not citizen_id:
        return {"errors": ["citizen_id is required to check eligibility."]}
    db = _db(config)
    try:
        eligibility = await rule_engine_service.evaluate_eligibility(db, citizen_id)
        conflicts = await conflict_engine_service.detect_conflicts_for_citizen(db, citizen_id)
        bundle = await optimizer_service.optimize_bundle_for_citizen(db, citizen_id)
        checklist = await checklist_service.generate_checklist(db, bundle["bundle_id"])
    except HTTPException as exc:
        return {"errors": [_http_error(exc)]}
    return {
        "eligibility_results": eligibility, "conflicts_results": conflicts,
        "bundle": bundle, "checklist": checklist,
    }


# --- Discovery / general policy Q&A --------------------------------------------------------

async def discovery_node(state: AgentState, config) -> dict:
    query = state.get("translated_query") or state["user_query"]
    result = await get_policy_service().retrieve_policy_evidence(query)
    if not result.verified:
        return {"retrieved_policy_evidence": [], "warnings": [result.note or "No matching policy evidence found."]}
    return {"retrieved_policy_evidence": [e.model_dump() for e in result.evidence]}


# --- Document verification subgraph --------------------------------------------------------

async def document_verification_node(state: AgentState, config) -> dict:
    citizen_id, scheme_id = state.get("citizen_id"), state.get("scheme_id")
    upload = state.get("uploaded_document") or {}
    if not citizen_id or not scheme_id or not upload.get("document_type"):
        return {"errors": ["citizen_id, scheme_id, and uploaded_document.document_type are required."]}
    db = _db(config)
    try:
        result = await document_verification_service.verify_document_for_citizen(
            db, citizen_id, scheme_id, upload["document_type"],
            pdf_base64=upload.get("pdf_base64"), document_text=upload.get("document_text"),
            declared_fields=upload.get("declared_fields") or {},
        )
    except HTTPException as exc:
        return {"errors": [_http_error(exc)]}
    return {
        "document_verification_result": result,
        "human_review_required": result["human_review_required"],
    }


async def fraud_screen_node(state: AgentState, config) -> dict:
    citizen_id = state.get("citizen_id")
    if not citizen_id:
        return {"errors": ["citizen_id is required for fraud screening."]}
    db = _db(config)
    try:
        result = await fraud_detection_service.screen_citizen_for_fraud(db, citizen_id, state.get("scheme_id"))
    except HTTPException as exc:
        return {"errors": [_http_error(exc)]}
    return {
        "fraud_risk_assessment": result,
        "human_review_required": result["human_review_required"] or bool(state.get("human_review_required")),
    }


async def human_review_node(state: AgentState, config) -> dict:
    if not state.get("human_review_required"):
        return {}
    decision = interrupt(
        {
            "reason": "Human review required before this result can be finalized.",
            "document_verification_result": state.get("document_verification_result"),
            "fraud_risk_assessment": state.get("fraud_risk_assessment"),
        }
    )
    return {"review_decision": decision}


def needs_human_review(state: AgentState) -> str:
    return "human_review" if state.get("human_review_required") else "final_response"


# --- Deadline / reminder subgraph -----------------------------------------------------------

async def deadline_node(state: AgentState, config) -> dict:
    scheme_id = state.get("scheme_id")
    if not scheme_id:
        return {"errors": ["scheme_id is required to look up a deadline."]}
    db = _db(config)
    result = await get_policy_service().retrieve_deadlines(scheme_id, db=db)
    return {
        "deadline_info": {
            "verified": result.verified,
            "evidence": [e.model_dump() for e in result.evidence],
            "note": result.note,
        }
    }


async def reminder_node(state: AgentState, config) -> dict:
    citizen_id, scheme_id = state.get("citizen_id"), state.get("scheme_id")
    if not citizen_id or not scheme_id:
        return {"errors": ["citizen_id and scheme_id are required to set a reminder."]}
    db = _db(config)
    try:
        result = await deadline_reminder_service.create_reminder(db, citizen_id, scheme_id, bool(state.get("consent")))
    except HTTPException as exc:
        return {"errors": [_http_error(exc)]}
    return {"deadline_info": {"reminder": result}}


# --- Grievance subgraph -----------------------------------------------------------------------

async def grievance_node(state: AgentState, config) -> dict:
    citizen_id = state.get("citizen_id")
    details = state.get("grievance_details") or {}
    if not citizen_id or not details.get("category") or not details.get("description"):
        return {"errors": ["citizen_id, grievance_details.category and .description are required."]}
    db = _db(config)
    try:
        result = await feedback_grievance_service.create_grievance(
            db, citizen_id, details["category"], details["description"], state.get("scheme_id")
        )
    except HTTPException as exc:
        return {"errors": [_http_error(exc)]}
    return {"grievance_ticket": result}


# --- Final response assembly ---------------------------------------------------------------

async def final_response_node(state: AgentState, config) -> dict:
    if state.get("errors"):
        return {"final_response": "; ".join(state["errors"])}

    intent = state.get("detected_intent")
    if intent in ("CHECK_ELIGIBILITY", "COMPARE_SCHEMES") and state.get("bundle"):
        bundle = state["bundle"]
        return {"final_response": bundle.get("explanation_text") or "No explanation available."}
    if intent in ("DISCOVER_SCHEME", "GENERAL_QUERY") and state.get("retrieved_policy_evidence"):
        top = state["retrieved_policy_evidence"][0]
        return {"final_response": f"{top['scheme_name']}: {top['content']}"}
    if intent == "VERIFY_DOCUMENT" and state.get("document_verification_result"):
        r = state["document_verification_result"]
        return {"final_response": f"Document status: {r['status']} (human review required: {r['human_review_required']})."}
    if intent == "CHECK_DEADLINE" and state.get("deadline_info"):
        info = state["deadline_info"]
        if info.get("verified"):
            return {"final_response": info["evidence"][0]["content"]}
        return {"final_response": info.get("note") or "No verified deadline found."}
    if intent == "SET_REMINDER" and state.get("deadline_info", {}).get("reminder"):
        return {"final_response": "Reminder recorded internally. No SMS/email is sent (no notification provider configured)."}
    if intent in ("REGISTER_GRIEVANCE", "SUBMIT_FEEDBACK", "CHECK_GRIEVANCE_STATUS") and state.get("grievance_ticket"):
        ticket = state["grievance_ticket"]
        return {"final_response": f"Internal ticket {ticket['ticket_id']} created (not an official government submission)."}
    if intent == "REPORT_SUSPICIOUS_ACTIVITY" and state.get("fraud_risk_assessment"):
        return {"final_response": state["fraud_risk_assessment"]["summary"]}
    if intent == "CHANGE_LANGUAGE":
        return {"final_response": "Language preference noted for this conversation."}
    return {"final_response": "I could not find a grounded answer for this request."}


# --- Graph assembly --------------------------------------------------------------------------

_ROUTES = {
    "DISCOVER_SCHEME": "discovery",
    "GENERAL_QUERY": "discovery",
    "COMPARE_SCHEMES": "scheme_recommendation",
    "CHECK_ELIGIBILITY": "scheme_recommendation",
    "VERIFY_DOCUMENT": "document_verification",
    "REPORT_SUSPICIOUS_ACTIVITY": "fraud_screen",
    "CHECK_DEADLINE": "deadline",
    "SET_REMINDER": "reminder",
    "REGISTER_GRIEVANCE": "grievance",
    "SUBMIT_FEEDBACK": "grievance",
    "CHECK_GRIEVANCE_STATUS": "grievance",
    "CHANGE_LANGUAGE": "final_response",
}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("language_in", language_in_node)
    graph.add_node("intent", intent_node)
    graph.add_node("discovery", discovery_node)
    graph.add_node("scheme_recommendation", scheme_recommendation_node)
    graph.add_node("document_verification", document_verification_node)
    graph.add_node("fraud_screen", fraud_screen_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("deadline", deadline_node)
    graph.add_node("reminder", reminder_node)
    graph.add_node("grievance", grievance_node)
    graph.add_node("final_response", final_response_node)
    graph.add_node("language_out", language_out_node)

    graph.add_edge(START, "language_in")
    graph.add_edge("language_in", "intent")
    graph.add_conditional_edges("intent", lambda s: _ROUTES.get(route_by_intent(s), "discovery"))

    graph.add_edge("discovery", "final_response")
    graph.add_edge("scheme_recommendation", "final_response")
    graph.add_edge("deadline", "final_response")
    graph.add_edge("reminder", "final_response")
    graph.add_edge("grievance", "final_response")

    # Document verification / fraud screening both feed the human-review gate before a
    # final response is produced (Section 9's Document Verification subgraph).
    graph.add_conditional_edges("document_verification", needs_human_review, {
        "human_review": "human_review", "final_response": "final_response",
    })
    graph.add_conditional_edges("fraud_screen", needs_human_review, {
        "human_review": "human_review", "final_response": "final_response",
    })
    graph.add_edge("human_review", "final_response")

    graph.add_edge("final_response", "language_out")
    graph.add_edge("language_out", END)

    return graph.compile(checkpointer=MemorySaver())


_compiled_graph = None


def get_compiled_graph():
    """Process-wide singleton — MemorySaver's checkpoints live in this instance, so a
    human-review resume (Section 9) must hit the same compiled graph that raised the
    interrupt. See workflow.py's module docstring for why a durable checkpointer would be a
    swap-in replacement rather than a redesign."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
