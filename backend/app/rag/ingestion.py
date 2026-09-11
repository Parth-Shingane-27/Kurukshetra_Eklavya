"""Ingestion pipeline (Section 3.2/3.3 of the brief): load -> validate/dedupe (already mostly
handled by loaders.py + the upstream clean_gov_schemes.py normalization pass) -> chunk -> embed
-> upsert into the vector store, plus a parallel BM25 index over the same chunks for hybrid
retrieval. Idempotent: chunk_id is deterministic (`{scheme_id}::{section}`), so re-running
upserts rather than duplicating.
"""

import logging

from app.rag.chunking import chunk_corpus
from app.rag.embeddings import embed_texts
from app.rag.loaders import load_gov_schemes_corpus
from app.rag.retriever import Bm25Index, build_bm25_index
from app.rag.vector_store import upsert_chunks

logger = logging.getLogger(__name__)


async def ingest_corpus(
    corpus_path: str,
    collection,
    api_key: str,
    embedding_model: str,
    bm25_index_path: str | None = None,
) -> dict:
    """Runs the full ingestion pipeline against an already-open Chroma collection.

    Returns a summary dict (scheme_count, chunk_count) for the caller (CLI script / tests) to
    report — ingestion never returns silently with no indication of what was indexed.
    """
    records = load_gov_schemes_corpus(corpus_path)
    chunks = chunk_corpus(records)
    if not chunks:
        logger.warning("No chunks produced from %d corpus records; nothing to ingest", len(records))
        return {"scheme_count": len(records), "chunk_count": 0}

    texts = [c.text for c in chunks]
    embeddings = await embed_texts(texts, api_key=api_key, model=embedding_model, task_type="RETRIEVAL_DOCUMENT")

    ids = [c.chunk_id for c in chunks]
    metadatas = [c.metadata.model_dump(exclude_none=True) for c in chunks]
    upsert_chunks(collection, ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    if bm25_index_path:
        bm25: Bm25Index = build_bm25_index(chunks)
        bm25.save(bm25_index_path)

    logger.info("Ingested %d schemes -> %d chunks into the vector store", len(records), len(chunks))
    return {"scheme_count": len(records), "chunk_count": len(chunks)}
