"""Ingestion pipeline (Section 3.2/3.3 of the brief): load -> validate/dedupe (already mostly
handled by loaders.py + the upstream clean_gov_schemes.py normalization pass) -> chunk -> embed
-> upsert into the vector store, plus a parallel BM25 index over the same chunks for hybrid
retrieval. Idempotent: chunk_id is deterministic (`{scheme_id}::{section}`), so re-running
upserts rather than duplicating.

Resumable by design: the free-tier embedding API enforces a *daily* request quota (observed:
1000 embedContent requests/day), and the full corpus can need several hundred batched requests
— comfortably possible to run out of quota mid-corpus. So this: (a) skips chunks already present
in the vector store (no quota spent re-embedding old work), and (b) upserts after *every* batch,
not once at the very end, so a run that's interrupted by a 429 still leaves everything it
completed actually persisted and queryable, rather than losing all progress. Re-running this
same script on a later day (once quota resets) picks up exactly where it left off.
"""

import logging

from app.rag.chunking import chunk_corpus
from app.rag.embeddings import EMBEDDING_BATCH_SIZE, embed_texts
from app.rag.loaders import load_gov_schemes_corpus
from app.rag.retriever import Bm25Index, build_bm25_index
from app.rag.vector_store import existing_ids, upsert_chunks

logger = logging.getLogger(__name__)


async def ingest_corpus(
    corpus_path: str,
    collection,
    api_key: str,
    embedding_model: str,
    bm25_index_path: str | None = None,
) -> dict:
    """Runs the full ingestion pipeline against an already-open Chroma collection.

    Returns a summary dict (scheme_count, chunk_count, newly_indexed_count, skipped_count) for
    the caller (CLI script / tests) to report — ingestion never returns silently with no
    indication of what was indexed. Raises (does not swallow) if quota/network failure stops it
    partway — whatever completed before the failure is already persisted (see module docstring).
    """
    records = load_gov_schemes_corpus(corpus_path)
    chunks = chunk_corpus(records)
    if not chunks:
        logger.warning("No chunks produced from %d corpus records; nothing to ingest", len(records))
        return {"scheme_count": len(records), "chunk_count": 0, "newly_indexed_count": 0, "skipped_count": 0}

    already_indexed = existing_ids(collection)
    pending = [c for c in chunks if c.chunk_id not in already_indexed]
    skipped_count = len(chunks) - len(pending)
    if skipped_count:
        logger.info("Skipping %d chunk(s) already present in the vector store", skipped_count)

    newly_indexed_count = 0
    for start in range(0, len(pending), EMBEDDING_BATCH_SIZE):
        batch = pending[start : start + EMBEDDING_BATCH_SIZE]
        texts = [c.text for c in batch]
        embeddings = await embed_texts(texts, api_key=api_key, model=embedding_model, task_type="RETRIEVAL_DOCUMENT")
        ids = [c.chunk_id for c in batch]
        metadatas = [c.metadata.model_dump(exclude_none=True) for c in batch]
        upsert_chunks(collection, ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        newly_indexed_count += len(batch)
        logger.info(
            "Persisted %d/%d newly-indexed chunks so far (this run)", newly_indexed_count, len(pending)
        )

    if bm25_index_path:
        # BM25 needs no embedding API calls, so it's always rebuilt over the FULL corpus
        # (including chunks skipped above) regardless of how much of this run's embedding work
        # actually completed — keyword search stays complete even mid-ingestion.
        bm25: Bm25Index = build_bm25_index(chunks)
        bm25.save(bm25_index_path)

    logger.info(
        "Ingested %d schemes -> %d total chunks (%d newly indexed this run, %d already present)",
        len(records), len(chunks), newly_indexed_count, skipped_count,
    )
    return {
        "scheme_count": len(records),
        "chunk_count": len(chunks),
        "newly_indexed_count": newly_indexed_count,
        "skipped_count": skipped_count,
    }
