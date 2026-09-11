"""LangGraph workflow tests (Section 8/9): intent routing to the correct node sequence,
state transitions, error propagation from a failing node, and the human-review
interrupt/resume cycle. No GEMINI_API_KEY in the test env, so language_in/out both take
their honest passthrough path, and discovery uses a mocked PolicyKnowledgeService (same
pattern as test_policy_search_api.py) rather than touching the real vector store.
"""

import uuid

from langgraph.types import Command

from app.graph.workflow import get_compiled_graph
from app.modules.scheme_kb.service import seed_schemes_if_empty
from app.rag.schemas import RetrievalResult, RetrievedEvidence

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1990-01-01",
    "state": "Bihar",
    "district": "Patna",
}


def _thread():
    return str(uuid.uuid4())


async def _create_citizen(client, **overrides):
    payload = {**BASE_CITIZEN, **overrides}
    res = await client.post("/api/citizens", json=payload)
    return res.json()["id"]


async def _pm_kisan_scheme_id(db):
    scheme = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    return str(scheme["_id"])


async def _invoke(db, thread_id, **state):
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id, "db": db}}
    initial = {"user_query": "", "errors": [], "warnings": [], **state}
    return await graph.ainvoke(initial, config=config)


class FakePolicyService:
    async def retrieve_policy_evidence(self, query, filters=None, top_k=5):
        return RetrievalResult(
            query=query, verified=True,
            evidence=[
                RetrievedEvidence(
                    content="Farmers with less than 5 acres qualify.",
                    scheme_id="corpus-1", scheme_name="Sample Farmer Scheme",
                    section="eligibility", source="dataset_provided",
                )
            ],
        )


async def test_discover_scheme_intent_routes_to_discovery(monkeypatch, client, db):
    monkeypatch.setattr("app.graph.workflow.get_policy_service", lambda: FakePolicyService())
    result = await _invoke(db, _thread(), user_query="What schemes are available for farmers?")
    assert result["detected_intent"] == "DISCOVER_SCHEME"
    assert result["retrieved_policy_evidence"][0]["scheme_name"] == "Sample Farmer Scheme"
    assert "Sample Farmer Scheme" in result["final_response"]


async def test_check_eligibility_intent_runs_full_pipeline(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    result = await _invoke(
        db, _thread(), user_query="Am I eligible for anything?", citizen_id=citizen_id,
    )
    assert result["detected_intent"] == "CHECK_ELIGIBILITY"
    assert result["bundle"] is not None
    assert result["checklist"] is not None
    assert result["final_response"] == result["bundle"]["explanation_text"]


async def test_check_eligibility_without_citizen_id_is_a_clean_error(client, db):
    result = await _invoke(db, _thread(), user_query="Check my eligibility please")
    assert result["errors"]
    assert "citizen_id is required" in result["final_response"]


async def test_check_eligibility_unknown_citizen_propagates_404_as_error(client, db):
    result = await _invoke(
        db, _thread(), user_query="Check my eligibility",
        citizen_id="64b7f0000000000000000000",
    )
    assert result["errors"]
    assert "404" in result["errors"][0]


async def test_verify_document_needs_review_triggers_interrupt_then_resume(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    thread_id = _thread()

    result = await _invoke(
        db, thread_id, user_query="Please verify document for me",
        citizen_id=citizen_id, scheme_id=scheme_id,
        uploaded_document={"document_type": "Passport", "document_text": "passport text"},
    )
    assert result["detected_intent"] == "VERIFY_DOCUMENT"
    assert result["document_verification_result"]["status"] == "needs_review"
    assert result["human_review_required"] is True
    assert "__interrupt__" in result  # graph paused for human review

    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id, "db": db}}
    resumed = await graph.ainvoke(Command(resume="approved"), config=config)
    assert resumed["review_decision"] == "approved"
    assert "__interrupt__" not in resumed
    assert "Document status: needs_review" in resumed["final_response"]


async def test_verify_document_clean_case_skips_human_review(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    result = await _invoke(
        db, _thread(), user_query="verify document",
        citizen_id=citizen_id, scheme_id=scheme_id,
        uploaded_document={"document_type": "Aadhaar Card", "document_text": "Aadhaar Card text"},
    )
    assert result["document_verification_result"]["status"] == "verified_structurally"
    assert result["human_review_required"] is False
    assert "__interrupt__" not in result


async def test_set_reminder_without_consent_is_a_clean_error(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    result = await _invoke(
        db, _thread(), user_query="Please remind me about this scheme",
        citizen_id=citizen_id, scheme_id=scheme_id,
    )
    assert result["errors"]
    assert "consent" in result["errors"][0].lower()


async def test_set_reminder_with_consent_never_claims_sent(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    result = await _invoke(
        db, _thread(), user_query="remind me please",
        citizen_id=citizen_id, scheme_id=scheme_id, consent=True,
    )
    reminder = result["deadline_info"]["reminder"]
    assert reminder["notification_sent"] is False
    assert "No SMS/email is sent" in result["final_response"]


async def test_register_grievance_intent_creates_internal_ticket(client, db):
    citizen_id = await _create_citizen(client)
    result = await _invoke(
        db, _thread(), user_query="I want to file a complaint",
        citizen_id=citizen_id,
        grievance_details={"category": "delay", "description": "Stuck for weeks."},
    )
    assert result["detected_intent"] == "REGISTER_GRIEVANCE"
    assert result["grievance_ticket"]["is_official_submission"] is False
    assert result["grievance_ticket"]["ticket_id"] in result["final_response"]


async def test_report_suspicious_activity_runs_fraud_screen(client, db):
    citizen_id = await _create_citizen(client)
    result = await _invoke(
        db, _thread(), user_query="I want to report fraud",
        citizen_id=citizen_id,
    )
    assert result["detected_intent"] == "REPORT_SUSPICIOUS_ACTIVITY"
    assert result["fraud_risk_assessment"]["risk_level"] == "low"  # no verifications on file
    assert result["final_response"] == result["fraud_risk_assessment"]["summary"]
