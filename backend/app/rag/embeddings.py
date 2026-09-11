"""Gemini embeddings wrapper (Section 3.5: reuses the existing google-genai dependency/API key
rather than adding a separate embedding provider). Kept isolated from vector_store.py so tests
can substitute a deterministic fake embedding function, the same pattern
`explanation/llm_client.py` uses for `call_gemini`.
"""

from google import genai
from google.genai import types

EMBEDDING_BATCH_SIZE = 50


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
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            response = await client.aio.models.embed_content(
                model=model,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type),
            )
        except Exception as exc:  # pragma: no cover - network/SDK failure path
            raise EmbeddingError(f"Gemini embedding call failed: {exc}") from exc
        if not response.embeddings or len(response.embeddings) != len(batch):
            raise EmbeddingError("Gemini embedding response did not match the requested batch size")
        vectors.extend(list(e.values) for e in response.embeddings)
    return vectors


async def embed_query(text: str, api_key: str, model: str) -> list[float]:
    vectors = await embed_texts([text], api_key, model, task_type="RETRIEVAL_QUERY")
    return vectors[0]
