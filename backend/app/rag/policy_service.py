"""Shared Policy Knowledge Service (Section 4 of the brief).

This is a *retrieval tool*, not a decision-maker: every 8-existing/5-new agent that needs
policy text calls into this one service rather than each re-implementing retrieval. It never
decides eligibility/conflicts/etc. — see Rule Engine boundary statement in plan.md Section 16,
which this service is designed to respect, not encroach on.

Grounding rule enforced here, not just documented: a scheme looked up in the curated Mongo
`schemes` collection is labeled `source="curated_knowledge_base"` (the app's own validated
data, still not an "official" third-party source unless `links.source_url`/`links.policy_url`
is a real, verified URL — see `SchemeLinks.application_link_status`, which this service does
NOT read or upgrade based on); anything from the vector corpus is labeled `source="dataset_provided"` since
`gov_schemes_cleaned.json` carries no verified source_url per scheme. Callers must not upgrade
either label themselves.
"""

import re

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingError, embed_query
from app.rag.retriever import Bm25Index, HybridRetriever
from app.rag.schemas import RetrievedEvidence, RetrievalResult
from app.rag.vector_store import get_persistent_collection

_DEADLINE_PATTERNS = [
    re.compile(r"within\s+\d+\s+(day|days|month|months|year|years)", re.IGNORECASE),
    re.compile(r"\b\d{1,2}(st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\bbefore\s+the\s+\d+\w*\s+of\b", re.IGNORECASE),
    re.compile(r"\blast\s+date\b", re.IGNORECASE),
]


def _is_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


def _extract_deadline_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if any(p.search(s) for p in _DEADLINE_PATTERNS)]


class PolicyKnowledgeService:
    def __init__(self, retriever: HybridRetriever, api_key: str, embedding_model: str):
        self._retriever = retriever
        self._api_key = api_key
        self._embedding_model = embedding_model

    async def _embed(self, query: str) -> list[float]:
        return await embed_query(query, api_key=self._api_key, model=self._embedding_model)

    async def retrieve_policy_evidence(
        self, query: str, filters: dict | None = None, top_k: int = 5
    ) -> RetrievalResult:
        """General-purpose grounded search over the policy corpus (Section 4).

        Retrieval failure (e.g. no GEMINI_API_KEY configured for embeddings) degrades to an
        honest "not verified" result rather than raising — the same BR-010 "never block the
        pipeline on LLM/embedding availability" principle the Explanation Agent already
        follows, extended to every RAG-backed call. Ingestion (app/rag/ingestion.py) is the
        one place a missing key stays a hard error, since there is nothing to index without it.
        """
        if not query.strip():
            return RetrievalResult(query=query, evidence=[], verified=False, note="Empty query.")
        try:
            embedding = await self._embed(query)
        except EmbeddingError:
            return RetrievalResult(
                query=query, evidence=[], verified=False,
                note="Policy retrieval is currently unavailable (embeddings not configured).",
            )
        evidence = self._retriever.retrieve(query, embedding, top_k=top_k, where=filters)
        if not evidence:
            return RetrievalResult(
                query=query, evidence=[], verified=False,
                note="No matching policy text could be retrieved for this query.",
            )
        return RetrievalResult(query=query, evidence=evidence, verified=True)

    async def retrieve_scheme_details(self, query: str, filters: dict | None = None) -> RetrievalResult:
        return await self.retrieve_policy_evidence(query, filters=filters, top_k=5)

    async def retrieve_eligibility_rules(
        self, scheme_id: str, query: str | None = None, db: AsyncIOMotorDatabase | None = None
    ) -> RetrievalResult:
        if db is not None and _is_object_id(scheme_id):
            scheme = await db.schemes.find_one({"_id": ObjectId(scheme_id)})
            if scheme is not None:
                evidence = [
                    RetrievedEvidence(
                        content=(
                            f"{scheme['name']}: requires "
                            + "; ".join(
                                f"{r['field_name']} {r['operator']} {r['value']!r}"
                                for r in scheme.get("rules", [])
                            )
                            if scheme.get("rules")
                            else f"{scheme['name']}: no eligibility rules declared."
                        ),
                        scheme_id=str(scheme["_id"]),
                        scheme_name=scheme["name"],
                        section="structured_rule",
                        source="curated_knowledge_base",
                        source_url=(scheme.get("links") or {}).get("policy_url")
                        or (scheme.get("links") or {}).get("source_url"),
                        metadata={"rules": scheme.get("rules", [])},
                    )
                ]
                return RetrievalResult(query=query or scheme_id, evidence=evidence, verified=True)
        return await self.retrieve_policy_evidence(
            query or "eligibility criteria", filters={"scheme_id": scheme_id, "section": "eligibility"}
        )

    async def retrieve_required_documents(
        self, scheme_id: str, db: AsyncIOMotorDatabase | None = None
    ) -> RetrievalResult:
        if db is not None and _is_object_id(scheme_id):
            scheme = await db.schemes.find_one({"_id": ObjectId(scheme_id)})
            if scheme is not None:
                reqs = scheme.get("document_requirements", [])
                evidence = [
                    RetrievedEvidence(
                        content=(
                            f"{req['document_type']} "
                            f"({'mandatory' if req.get('is_mandatory', True) else 'optional'})"
                        ),
                        scheme_id=str(scheme["_id"]),
                        scheme_name=scheme["name"],
                        section="structured_rule",
                        source="curated_knowledge_base",
                        source_url=(scheme.get("links") or {}).get("source_url"),
                        metadata=req,
                    )
                    for req in reqs
                ]
                return RetrievalResult(
                    query=scheme_id, evidence=evidence, verified=bool(evidence),
                    note=None if evidence else "No document requirements declared for this scheme.",
                )
        return await self.retrieve_policy_evidence(
            "required documents", filters={"scheme_id": scheme_id, "section": "documents"}
        )

    async def retrieve_deadlines(self, scheme_id: str, db: AsyncIOMotorDatabase | None = None) -> RetrievalResult:
        """Never invents a date (Section 7.2/11). Extracts deadline-shaped sentences from
        retrieved application/eligibility/benefits text; returns verified=False (not a guess)
        when nothing matches."""
        result = await self.retrieve_policy_evidence(
            "application deadline last date closing date",
            filters={"scheme_id": scheme_id},
            top_k=10,
        )
        deadline_evidence: list[RetrievedEvidence] = []
        for item in result.evidence:
            for sentence in _extract_deadline_sentences(item.content):
                deadline_evidence.append(item.model_copy(update={"content": sentence}))
        if not deadline_evidence:
            return RetrievalResult(
                query=result.query, evidence=[], verified=False,
                note="No explicit deadline language found in the available policy text for this scheme.",
            )
        return RetrievalResult(query=result.query, evidence=deadline_evidence, verified=True)

    async def retrieve_grievance_procedure(
        self, scheme_id: str | None = None, db: AsyncIOMotorDatabase | None = None
    ) -> RetrievalResult:
        if scheme_id and db is not None and _is_object_id(scheme_id):
            scheme = await db.schemes.find_one({"_id": ObjectId(scheme_id)})
            if scheme is not None and scheme.get("issuing_authority"):
                evidence = [
                    RetrievedEvidence(
                        content=f"Issuing authority: {scheme['issuing_authority']}",
                        scheme_id=str(scheme["_id"]),
                        scheme_name=scheme["name"],
                        section="structured_rule",
                        source="curated_knowledge_base",
                        source_url=(scheme.get("links") or {}).get("grievance_url")
                        or (scheme.get("links") or {}).get("source_url"),
                        metadata={"issuing_authority": scheme["issuing_authority"]},
                    )
                ]
                return RetrievalResult(query=scheme_id, evidence=evidence, verified=True)
        filters = {"scheme_id": scheme_id} if scheme_id else None
        result = await self.retrieve_policy_evidence(
            "grievance complaint appeal contact department", filters=filters, top_k=5
        )
        if not result.evidence:
            return RetrievalResult(
                query=result.query, evidence=[], verified=False,
                note="No grievance/department contact information found for this scheme in the "
                "available data. An internal platform ticket can still be raised.",
            )
        return result


class _LazyRetriever:
    """Defers opening the persistent Chroma collection/BM25 index until the first vector
    search actually happens. Several PolicyKnowledgeService methods (retrieve_eligibility_rules,
    retrieve_required_documents, retrieve_grievance_procedure) resolve entirely against the
    curated Mongo `schemes` collection and never touch the vector store at all — those callers
    (e.g. the Document Verification Agent looking up a curated scheme's requirements)
    shouldn't pay the cost of opening a Chroma client, or need GEMINI_API_KEY, just because
    get_policy_service() was called once."""

    def __init__(self, persist_dir: str, bm25_index_path: str):
        self._persist_dir = persist_dir
        self._bm25_index_path = bm25_index_path
        self._real: HybridRetriever | None = None

    def _ensure_built(self) -> HybridRetriever:
        if self._real is None:
            collection = get_persistent_collection(self._persist_dir)
            bm25_index = None
            try:
                bm25_index = Bm25Index.load(self._bm25_index_path)
            except FileNotFoundError:
                pass
            self._real = HybridRetriever(collection, bm25_index=bm25_index)
        return self._real

    def retrieve(self, *args, **kwargs):
        return self._ensure_built().retrieve(*args, **kwargs)


_service: PolicyKnowledgeService | None = None


def get_policy_service() -> PolicyKnowledgeService:
    """FastAPI-dependency-style singleton accessor, mirroring app.core.db.get_db()'s pattern.
    Cheap to call repeatedly — see _LazyRetriever above for why opening the vector store is
    deferred rather than done here."""
    global _service
    if _service is None:
        settings = get_settings()
        retriever = _LazyRetriever(settings.chroma_persist_dir, settings.bm25_index_path)
        _service = PolicyKnowledgeService(
            retriever, api_key=settings.gemini_api_key or "", embedding_model=settings.embedding_model
        )
    return _service


def reset_policy_service() -> None:
    """Test-only hook to force get_policy_service() to rebuild (new persist dir/mocks)."""
    global _service
    _service = None
