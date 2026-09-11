"""Field-based chunking (Section 3.4 of the brief): the corpus already segments each scheme
into semantically-bounded prose fields (details/eligibility/benefits/application/documents),
so chunking is "one chunk per non-empty field" rather than a character-count splitter — this
is what "preserve semantic boundaries... do not split important rules in a way that loses
their meaning" means for this dataset shape.
"""

from app.rag.schemas import PolicyChunk, PolicyChunkMetadata

# Maps a corpus JSON field to the PolicySection label used in metadata/citations.
SECTION_FIELDS: dict[str, str] = {
    "details": "details",
    "eligibility": "eligibility",
    "benefits": "benefits",
    "application": "application",
    "documents": "documents",
}


def chunk_scheme_record(record: dict) -> list[PolicyChunk]:
    """One PolicyChunk per non-empty section field of a corpus record."""
    scheme_id = str(record["scheme_id"])
    scheme_name = str(record["scheme_name"])
    category = ", ".join(record.get("scheme_category_list") or []) or record.get("scheme_category") or None
    level = record.get("level") or None

    chunks: list[PolicyChunk] = []
    for field_name, section in SECTION_FIELDS.items():
        text = (record.get(field_name) or "").strip()
        if not text:
            continue
        metadata = PolicyChunkMetadata(
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            category=category,
            level=level,
            document_type="scheme_catalog_entry",
            section=section,  # type: ignore[arg-type]
            source="dataset_provided",
            source_url=None,  # the corpus carries no verified official URL per scheme
            language="en",
            policy_version=None,
            last_updated=None,
        )
        chunks.append(
            PolicyChunk(chunk_id=f"{scheme_id}::{section}", text=text, metadata=metadata)
        )
    return chunks


def chunk_corpus(records: list[dict]) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for record in records:
        chunks.extend(chunk_scheme_record(record))
    return chunks
