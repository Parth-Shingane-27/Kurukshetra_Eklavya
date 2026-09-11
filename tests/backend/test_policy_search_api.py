"""API tests for the /api/policy/* router (Section 14: "example end-to-end retrieval
results" reachable over HTTP). Overrides the get_policy_service dependency with a service
backed by an ephemeral Chroma collection + deterministic fake embeddings, the same pattern
`conftest.py`'s `db` fixture uses for mongomock — no real network call in the suite.
"""

import hashlib

import pytest_asyncio

from app.main import app
from app.rag.chunking import chunk_corpus
from app.rag.ingestion import ingest_corpus
from app.rag.policy_service import PolicyKnowledgeService, get_policy_service
from app.rag.retriever import HybridRetriever, build_bm25_index
from app.rag.vector_store import get_ephemeral_collection

DIMS = 32


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
        "scheme_id": 201,
        "scheme_name": "Weavers Support Scheme",
        "details": "Support for handloom weavers.",
        "eligibility": "Applicant must be a registered handloom weaver.",
        "benefits": "Subsidy of Rs 5000.",
        "application": "Apply within 45 days of enrollment.",
        "documents": "Weaver ID Card.",
        "level": "State",
    }
]


@pytest_asyncio.fixture(autouse=True)
async def override_policy_service(monkeypatch):
    monkeypatch.setattr("app.rag.ingestion.embed_texts", _fake_embed_texts)

    collection = get_ephemeral_collection()
    import json
    import tempfile
    from pathlib import Path

    fd_path = tempfile.mkstemp(suffix=".json")[1]
    Path(fd_path).write_text(json.dumps(FIXTURE_RECORDS), encoding="utf-8")
    await ingest_corpus(
        corpus_path=fd_path, collection=collection, api_key="fake-key",
        embedding_model="fake-model", bm25_index_path=None,
    )
    bm25_index = build_bm25_index(chunk_corpus(FIXTURE_RECORDS))
    service = PolicyKnowledgeService(
        HybridRetriever(collection, bm25_index=bm25_index), api_key="fake-key", embedding_model="fake-model"
    )
    monkeypatch.setattr(service, "_embed", lambda query: _fake_embed_query(query, "fake-key", "fake-model"))

    app.dependency_overrides[get_policy_service] = lambda: service
    yield
    app.dependency_overrides.pop(get_policy_service, None)


async def test_search_endpoint_returns_grounded_evidence(client):
    resp = await client.get("/api/policy/search", params={"q": "handloom weavers subsidy"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["evidence"][0]["scheme_id"] == "201"
    assert body["evidence"][0]["source"] == "dataset_provided"


async def test_search_endpoint_requires_query_param(client):
    resp = await client.get("/api/policy/search")
    assert resp.status_code == 422


async def test_scheme_deadlines_endpoint_extracts_deadline_text(client):
    resp = await client.get("/api/policy/schemes/201/deadlines")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert any("45 days" in e["content"] for e in body["evidence"])


async def test_scheme_documents_endpoint_no_curated_scheme_falls_back_to_corpus(client):
    resp = await client.get("/api/policy/schemes/201/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["evidence"][0]["scheme_id"] == "201"


async def test_grievance_endpoint_honest_when_nothing_found(client):
    resp = await client.get("/api/policy/grievance", params={"scheme_id": "999"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is False
    assert "internal platform ticket" in body["note"]
