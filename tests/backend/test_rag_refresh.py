"""FR-015 — RAG-Based Knowledge Base Freshness (BR-015: candidates only, never auto-committed)."""

from app.core.config import get_settings
from app.models.rag_candidate import RagCandidateDraft, RagProposedChanges
from app.modules.rag_refresh import service
from app.rag.schemas import RetrievalResult, RetrievedEvidence

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

SCHEME = {
    "name": "RAG Refresh Test Grant",
    "description": "Old description on file.",
    "category": "Agriculture,Rural & Environment",
    "benefit_type": "cash_transfer",
    "benefit_value_estimate": 1000,
    "rules": [],
    "document_requirements": [{"document_type": "Aadhaar Card", "is_mandatory": True}],
    "links": {"application_url": "https://old.example.gov.in/", "application_link_status": "verified"},
}


class _FakeSettingsWithKey:
    gemini_api_key = "fake-key"
    gemini_model = "gemini-2.0-flash"


class _FakeSettingsNoKey:
    gemini_api_key = None
    gemini_model = "gemini-2.0-flash"


class _FakePolicyService:
    def __init__(self, result):
        self._result = result

    async def retrieve_scheme_details(self, query, filters=None):
        return self._result


class _FakeStructuredLLM:
    def __init__(self, draft=None, raise_error=False):
        self._draft = draft
        self._raise_error = raise_error

    async def ainvoke(self, prompt):
        if self._raise_error:
            raise RuntimeError("simulated LLM failure")
        return self._draft


class _FakeChatModel:
    def __init__(self, draft=None, raise_error=False):
        self._draft = draft
        self._raise_error = raise_error

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(self._draft, self._raise_error)


def _fake_chat_model_factory(draft=None, raise_error=False):
    def factory(model, google_api_key):
        return _FakeChatModel(draft, raise_error)
    return factory


async def _create_scheme(client, scheme=None):
    res = await client.post("/api/schemes", json=scheme or SCHEME, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    return res.json()["id"]


def _verified_evidence_result(scheme_id):
    return RetrievalResult(
        query="q",
        evidence=[
            RetrievedEvidence(
                content="This scheme now pays Rs 2500 per year.",
                scheme_id=scheme_id,
                scheme_name="RAG Refresh Test Grant",
                section="benefits",
                source="dataset_provided",
                source_url="https://gov.example.in/notification",
            )
        ],
        verified=True,
    )


async def test_no_evidence_produces_no_candidate(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(
        service, "get_policy_service", lambda: _FakePolicyService(RetrievalResult(query="q", evidence=[], verified=False))
    )

    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    assert candidate is None
    assert await db.rag_candidate_updates.count_documents({}) == 0


async def test_no_gemini_key_produces_no_candidate(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsNoKey())

    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    assert candidate is None
    assert await db.rag_candidate_updates.count_documents({}) == 0


async def test_drafting_failure_produces_no_candidate(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(raise_error=True))

    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    assert candidate is None
    assert await db.rag_candidate_updates.count_documents({}) == 0


async def test_draft_with_no_confident_fields_produces_no_candidate(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    empty_draft = RagCandidateDraft(proposed_changes=RagProposedChanges(), confidence=0.1, rationale="Nothing grounded.")
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(draft=empty_draft))

    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    assert candidate is None
    assert await db.rag_candidate_updates.count_documents({}) == 0


async def test_refresh_creates_pending_candidate_without_touching_schemes(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    draft = RagCandidateDraft(
        proposed_changes=RagProposedChanges(benefit_value_estimate=2500, application_url="https://new.example.gov.in/"),
        confidence=0.9,
        rationale="Notification explicitly states the new amount and portal.",
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(draft=draft))

    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    assert candidate is not None
    assert candidate["status"] == "pending"
    assert candidate["proposed_changes"]["benefit_value_estimate"] == 2500
    assert candidate["source_passages"][0]["source_url"] == "https://gov.example.in/notification"

    # Never auto-committed to the live scheme (BR-015).
    scheme_res = await client.get(f"/api/schemes/{scheme_id}")
    assert scheme_res.json()["benefit_value_estimate"] == 1000


async def test_approve_candidate_commits_via_update_scheme_path(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    draft = RagCandidateDraft(
        proposed_changes=RagProposedChanges(
            benefit_value_estimate=2500,
            application_url="https://new.example.gov.in/",
            document_requirements=["Aadhaar Card", "Bank Passbook"],
        ),
        confidence=0.9,
        rationale="Grounded in the retrieved notification.",
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(draft=draft))
    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    approved = await service.approve_candidate(db, candidate["id"])
    assert approved["status"] == "approved"

    scheme_res = await client.get(f"/api/schemes/{scheme_id}")
    scheme = scheme_res.json()
    assert scheme["benefit_value_estimate"] == 2500
    assert scheme["links"]["application_url"] == "https://new.example.gov.in/"
    # Never auto-upgraded to "verified" just because a curator approved the candidate (NFR-016).
    assert scheme["links"]["application_link_status"] == "unverified"
    doc_types = {d["document_type"] for d in scheme["document_requirements"]}
    assert doc_types == {"Aadhaar Card", "Bank Passbook"}


async def test_reject_candidate_leaves_scheme_untouched(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    draft = RagCandidateDraft(
        proposed_changes=RagProposedChanges(benefit_value_estimate=9999),
        confidence=0.9,
        rationale="x",
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(draft=draft))
    candidate = await service.refresh_scheme_candidate(db, scheme_id)

    rejected = await service.reject_candidate(db, candidate["id"], reason="Source looks outdated")
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Source looks outdated"

    scheme_res = await client.get(f"/api/schemes/{scheme_id}")
    assert scheme_res.json()["benefit_value_estimate"] == 1000


async def test_approve_already_reviewed_candidate_returns_400(client, db, monkeypatch):
    scheme_id = await _create_scheme(client)
    monkeypatch.setattr(service, "get_policy_service", lambda: _FakePolicyService(_verified_evidence_result(scheme_id)))
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    draft = RagCandidateDraft(proposed_changes=RagProposedChanges(benefit_value_estimate=2500), confidence=0.9, rationale="x")
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _fake_chat_model_factory(draft=draft))
    candidate = await service.refresh_scheme_candidate(db, scheme_id)
    await service.approve_candidate(db, candidate["id"])

    import pytest
    from fastapi import HTTPException

    try:
        await service.approve_candidate(db, candidate["id"])
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


async def test_rag_endpoints_require_admin(client):
    res = await client.get("/api/admin/rag-candidates")
    assert res.status_code in (401, 403)

    res = await client.post("/api/admin/rag/refresh", params={"scheme_id": "000000000000000000000000"})
    assert res.status_code in (401, 403)


def test_structural_core_engines_never_read_rag_candidate_updates():
    """BR-015's most important test: the Rule Engine, Conflict Detection Engine, and Bundle
    Optimizer must never reference `rag_candidate_updates` — a RAG-sourced candidate must be
    architecturally incapable of influencing a live eligibility/conflict/bundle decision before
    a curator approves it into `schemes`."""
    import pathlib

    core_engine_files = [
        "backend/app/modules/rule_engine/engine.py",
        "backend/app/modules/rule_engine/service.py",
        "backend/app/modules/conflict_engine/engine.py",
        "backend/app/modules/conflict_engine/service.py",
        "backend/app/modules/optimizer/engine.py",
        "backend/app/modules/optimizer/service.py",
    ]
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    for rel_path in core_engine_files:
        text = (repo_root / rel_path).read_text(encoding="utf-8")
        assert "rag_candidate_updates" not in text, f"{rel_path} must never reference rag_candidate_updates"
