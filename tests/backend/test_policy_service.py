"""PolicyKnowledgeService / hybrid retrieval tests (Section 13: retrieval by scheme,
category, no-result handling, source traceability). Uses Chroma's EphemeralClient (in-memory,
mirrors mongomock's isolated-per-test pattern) and a deterministic hashed bag-of-words fake
embedding so no network call is ever made in the suite — same convention as the existing
mocked `call_gemini` in the Explanation Agent's tests.
"""

import hashlib

import pytest
import pytest_asyncio
from bson import ObjectId

from app.rag.chunking import chunk_corpus
from app.rag.ingestion import ingest_corpus
from app.rag.policy_service import PolicyKnowledgeService
from app.rag.retriever import HybridRetriever, build_bm25_index
from app.rag.vector_store import get_ephemeral_collection

DIMS = 64


def _fake_vector(text: str) -> list[float]:
    vector = [0.0] * DIMS
    for token in text.lower().split():
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % DIMS
        vector[idx] += 1.0
    return vector


async def _fake_embed_texts(texts, api_key, model, task_type="RETRIEVAL_DOCUMENT", batch_size=50):
    return [_fake_vector(t) for t in texts]


async def _fake_embed_query(text, api_key, model):
    return _fake_vector(text)


FIXTURE_RECORDS = [
    {
        "scheme_id": 101,
        "scheme_name": "Fisherman Relief Assistance",
        "details": "Financial assistance for fishermen families in Puducherry.",
        "eligibility": "The missing fisherman must have been in the age group of 18-60 years and a resident of Puducherry.",
        "benefits": "Rs 100000 immediate relief assistance in two installments.",
        "application": "Submit the application within 30 days from the date of the event.",
        "documents": "Photograph. Residential Certificate. FIR copy.",
        "level": "State",
        "scheme_category_list": ["Social welfare"],
    },
    {
        "scheme_id": 102,
        "scheme_name": "Student Scholarship Programme",
        "details": "Scholarship for meritorious students from economically weaker sections.",
        "eligibility": "Applicant must be enrolled in a recognized institution and family income below Rs 250000.",
        "benefits": "Annual scholarship of Rs 20000.",
        "application": "Apply through the national scholarship portal. Last date is announced yearly.",
        "documents": "Income Certificate. Bonafide Certificate.",
        "level": "Central",
        "scheme_category_list": ["Education"],
    },
]


@pytest_asyncio.fixture
async def policy_service(monkeypatch):
    monkeypatch.setattr("app.rag.ingestion.embed_texts", _fake_embed_texts)
    monkeypatch.setattr("app.rag.policy_service.embed_query", _fake_embed_query)

    collection = get_ephemeral_collection()
    await ingest_corpus(
        corpus_path=_write_fixture(),
        collection=collection,
        api_key="fake-key",
        embedding_model="fake-model",
        bm25_index_path=None,
    )
    chunks = chunk_corpus(FIXTURE_RECORDS)
    bm25_index = build_bm25_index(chunks)
    retriever = HybridRetriever(collection, bm25_index=bm25_index)
    return PolicyKnowledgeService(retriever, api_key="fake-key", embedding_model="fake-model")


def _write_fixture() -> str:
    import json
    import tempfile
    from pathlib import Path

    fd, path = tempfile.mkstemp(suffix=".json")
    import os

    os.close(fd)
    Path(path).write_text(json.dumps(FIXTURE_RECORDS), encoding="utf-8")
    return path


async def test_retrieve_policy_evidence_finds_matching_scheme(policy_service):
    result = await policy_service.retrieve_policy_evidence("fisherman relief assistance")
    assert result.verified is True
    assert result.evidence
    assert result.evidence[0].scheme_id == "101"
    assert result.evidence[0].source == "dataset_provided"
    assert result.evidence[0].source_url is None


async def test_retrieve_policy_evidence_no_result_is_honest(policy_service):
    # An empty query must never claim verification, regardless of what a fake embedding
    # might otherwise return for it.
    result = await policy_service.retrieve_policy_evidence("")
    assert result.verified is False
    assert result.evidence == []
    assert result.note


async def test_retrieve_policy_evidence_filters_by_scheme_id(policy_service):
    result = await policy_service.retrieve_policy_evidence(
        "eligibility documents", filters={"scheme_id": "102"}
    )
    assert result.verified is True
    assert all(e.scheme_id == "102" for e in result.evidence)


async def test_retrieve_deadlines_extracts_deadline_language(policy_service):
    result = await policy_service.retrieve_deadlines("101")
    assert result.verified is True
    assert any("30 days" in e.content for e in result.evidence)


async def test_retrieve_deadlines_honest_when_scheme_has_none(policy_service):
    # scheme_id "999" doesn't exist in the corpus at all -> nothing retrieved -> not verified.
    result = await policy_service.retrieve_deadlines("999")
    assert result.verified is False
    assert result.evidence == []
    assert "not" in (result.note or "").lower() or "no" in (result.note or "").lower()


async def test_retrieve_eligibility_rules_uses_curated_mongo_scheme_when_available(policy_service, db):
    scheme_doc = {
        "name": "Curated PM-KISAN-like Scheme",
        "rules": [{"field_name": "occupation", "operator": "=", "value": "farmer", "logical_group": "A"}],
        "document_requirements": [],
        "is_active": True,
        "source_reference": "https://example.gov.in/scheme",
    }
    inserted = await db.schemes.insert_one(scheme_doc)
    scheme_id = str(inserted.inserted_id)

    result = await policy_service.retrieve_eligibility_rules(scheme_id, db=db)
    assert result.verified is True
    assert result.evidence[0].source == "curated_knowledge_base"
    assert result.evidence[0].source_url == "https://example.gov.in/scheme"
    assert "occupation" in result.evidence[0].content


async def test_retrieve_grievance_procedure_honest_when_nothing_found(policy_service, db):
    result = await policy_service.retrieve_grievance_procedure(scheme_id="999", db=db)
    assert result.verified is False
    assert "internal platform ticket" in (result.note or "")
