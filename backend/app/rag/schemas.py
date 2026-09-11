"""Structured retrieval types shared by every RAG-backed call.

Every retrieved piece of evidence carries where it came from (source/section/scheme) so a
caller (an agent, the Explanation module, a test) can cite it rather than treat retrieval as
an opaque string blob. See rag/policy_service.py's module docstring for the honesty rule this
schema exists to enforce: a result with no real source_url must never be labeled "official."
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Corpus-provided fields aren't independently verified against an official portal; a scheme
# looked up in the curated Mongo `schemes` collection *is* the app's own validated data.
SourceKind = Literal["dataset_provided", "curated_knowledge_base"]

PolicySection = Literal[
    "details", "eligibility", "benefits", "application", "documents", "structured_rule"
]

DocumentType = Literal["scheme_catalog_entry", "curated_scheme_record"]


class PolicyChunkMetadata(BaseModel):
    """Metadata attached to every indexed chunk (Section 3.7 of the brief)."""

    scheme_id: str
    scheme_name: str
    category: str | None = None
    level: str | None = None  # "Central" / "State" / "UT" as given by the source dataset
    document_type: DocumentType
    section: PolicySection
    source: SourceKind
    source_url: str | None = None
    language: str = "en"
    policy_version: str | None = None
    last_updated: str | None = None


class PolicyChunk(BaseModel):
    """One unit of text handed to the embedding model / vector store."""

    chunk_id: str
    text: str
    metadata: PolicyChunkMetadata


class RetrievedEvidence(BaseModel):
    """One retrieval hit, returned to a calling agent — never raw text with no provenance."""

    content: str
    scheme_id: str
    scheme_name: str
    section: PolicySection
    source: SourceKind
    source_url: str | None = None
    policy_version: str | None = None
    last_updated: str | None = None
    relevance_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Envelope returned by every PolicyKnowledgeService method."""

    query: str
    evidence: list[RetrievedEvidence]
    verified: bool
    """False when nothing could be retrieved — callers must say "could not be verified",
    never silently proceed as if verified is implicitly true."""
    note: str | None = None
