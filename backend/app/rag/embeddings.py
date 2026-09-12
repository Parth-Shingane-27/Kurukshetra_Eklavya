"""Gemini embeddings wrapper (Section 3.5: reuses the existing google-genai dependency/API key
rather than adding a separate embedding provider). Kept isolated from vector_store.py so tests
can substitute a deterministic fake embedding function, the same pattern
`explanation/llm_client.py` uses for `call_gemini`.
"""

import asyncio
import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 50
MAX_RETRIES_PER_BATCH = 5
INTER_BATCH_DELAY_SECONDS = 1.0
"""A deliberate pause between successful batches — the free tier's embedContent quota is
per-minute (observed: 100 requests/min), not per-day, so a full-corpus ingestion (hundreds of
batches) only needs to not burst faster than that, not stop entirely."""


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be produced — ingestion must fail loudly on this (Section
    RAG layer notes: unlike the optional explanation LLM call, there is no RAG without
    embeddings, so this is never silently swallowed)."""


async def embed_texts(
    texts: list[str],
    api_key: str,
    model: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """Embed a batch of texts. `task_type` should be RETRIEVAL_DOCUMENT when indexing and
    RETRIEVAL_QUERY when embedding a search query — Gemini's embedding models are tuned per
    task_type and mixing them measurably hurts retrieval quality."""
    if not api_key:
        raise EmbeddingError(
            "GEMINI_API_KEY is not set. Embeddings require a real API key — this is a hard "
            "requirement for RAG ingestion/retrieval, unlike the optional explanation fallback."
        )
    if not texts:
        return []

    client = genai.Client(api_key=api_key)
    vectors: list[list[float]] = []
    num_batches = (len(texts) + batch_size - 1) // batch_size
    for batch_index, start in enumerate(range(0, len(texts), batch_size)):
        batch = texts[start : start + batch_size]
        response = None
        for attempt in range(1, MAX_RETRIES_PER_BATCH + 1):
            try:
                response = await client.aio.models.embed_content(
                    model=model,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                break
            except genai_errors.ClientError as exc:
                is_rate_limit = getattr(exc, "code", None) == 429
                if not is_rate_limit or attempt == MAX_RETRIES_PER_BATCH:
                    raise EmbeddingError(f"Gemini embedding call failed: {exc}") from exc
                # The free tier's embedContent quota is per-minute, not per-day (unlike
                # generateContent's daily cap) — a short backoff and retry is the correct
                # response, not treating this as a hard failure.
                backoff_seconds = min(60, 10 * attempt)
                logger.warning(
                    "Embedding batch %d/%d rate-limited (attempt %d/%d) — retrying in %ds",
                    batch_index + 1, num_batches, attempt, MAX_RETRIES_PER_BATCH, backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
            except Exception as exc:  # pragma: no cover - network/SDK failure path
                raise EmbeddingError(f"Gemini embedding call failed: {exc}") from exc
        if not response.embeddings or len(response.embeddings) != len(batch):
            raise EmbeddingError("Gemini embedding response did not match the requested batch size")
        vectors.extend(list(e.values) for e in response.embeddings)
        logger.info("Embedded batch %d/%d (%d texts)", batch_index + 1, num_batches, len(batch))
        if batch_index + 1 < num_batches:
            await asyncio.sleep(INTER_BATCH_DELAY_SECONDS)
    return vectors


async def embed_query(text: str, api_key: str, model: str) -> list[float]:
    vectors = await embed_texts([text], api_key, model, task_type="RETRIEVAL_QUERY")
    return vectors[0]
