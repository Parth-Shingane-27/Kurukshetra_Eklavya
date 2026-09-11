"""CLI entry point for the RAG ingestion pipeline (Section 3.2 of the brief).

Usage (from repo root):
    source backend/.venv/bin/activate
    python backend/scripts/ingest_policies.py

Requires GEMINI_API_KEY to be set (embeddings are not optional for RAG, unlike the
Explanation Agent's template-fallback LLM call). Reads backend/.env via the same
pydantic-settings config the API server uses, so no separate configuration is needed.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on sys.path

from app.core.config import get_settings  # noqa: E402
from app.rag.ingestion import ingest_corpus  # noqa: E402
from app.rag.vector_store import count, get_persistent_collection  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ingest_policies")


async def main() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not set (backend/.env) — cannot generate embeddings.")
        sys.exit(1)

    backend_dir = Path(__file__).resolve().parents[1]
    corpus_path = (backend_dir / settings.policy_corpus_path).resolve()
    persist_dir = (backend_dir / settings.chroma_persist_dir).resolve()
    bm25_path = (backend_dir / settings.bm25_index_path).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)
    bm25_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Corpus: %s", corpus_path)
    logger.info("Chroma persist dir: %s", persist_dir)

    collection = get_persistent_collection(str(persist_dir))
    summary = await ingest_corpus(
        corpus_path=str(corpus_path),
        collection=collection,
        api_key=settings.gemini_api_key,
        embedding_model=settings.embedding_model,
        bm25_index_path=str(bm25_path),
    )

    logger.info(
        "Done: %d schemes -> %d chunks indexed. Collection now holds %d chunks total.",
        summary["scheme_count"], summary["chunk_count"], count(collection),
    )


if __name__ == "__main__":
    asyncio.run(main())
