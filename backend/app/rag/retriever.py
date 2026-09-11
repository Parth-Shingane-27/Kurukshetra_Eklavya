"""Hybrid retrieval (Section 10 of the brief): combines Chroma's vector search with a
BM25 keyword index over the same chunk corpus, since a pure embedding search alone misses
exact scheme-name / acronym matches that citizens and admins actually type. Also enforces the
project's retrieval-quality guardrails: metadata filtering, top-k, no-result handling, and
never silently mixing chunks from different schemes/levels into one synthesized answer (each
hit stays attributed to its own scheme_id).
"""

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.rag.schemas import PolicyChunk, RetrievedEvidence

_TOKEN_RE = re.compile(r"[a-z0-9]+")

VECTOR_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4
BM25_CANDIDATE_MULTIPLIER = 4


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Bm25Index:
    bm25: BM25Okapi
    chunk_ids: list[str]

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(pickle.dumps(self))

    @classmethod
    def load(cls, path: str | Path) -> "Bm25Index":
        return pickle.loads(Path(path).read_bytes())


def build_bm25_index(chunks: list[PolicyChunk]) -> Bm25Index:
    tokenized = [_tokenize(c.text) for c in chunks]
    return Bm25Index(bm25=BM25Okapi(tokenized), chunk_ids=[c.chunk_id for c in chunks])


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _matches_where(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    return all(metadata.get(k) == v for k, v in where.items())


def _to_chroma_where(where: dict | None) -> dict | None:
    """Chroma requires a `where` dict to have exactly one top-level key; multiple equality
    filters must be combined under `$and`."""
    if not where:
        return None
    if len(where) == 1:
        return where
    return {"$and": [{k: v} for k, v in where.items()]}


class HybridRetriever:
    """Wraps a Chroma collection (vector search + metadata + document storage) and an
    optional BM25 index (keyword search) over the identical chunk set."""

    def __init__(self, collection, bm25_index: Bm25Index | None = None):
        self._collection = collection
        self._bm25_index = bm25_index

    def retrieve(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[RetrievedEvidence]:
        vector_scores: dict[str, float] = {}
        vector_result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * BM25_CANDIDATE_MULTIPLIER, top_k),
            where=_to_chroma_where(where),
            include=["documents", "metadatas", "distances"],
        )
        ids = vector_result.get("ids", [[]])[0]
        distances = vector_result.get("distances", [[]])[0]
        for cid, dist in zip(ids, distances):
            # Chroma default distance is smaller-is-better; convert to a larger-is-better score.
            vector_scores[cid] = -dist

        keyword_scores: dict[str, float] = {}
        if self._bm25_index is not None and query_text.strip():
            tokens = _tokenize(query_text)
            if tokens:
                scores = self._bm25_index.bm25.get_scores(tokens)
                ranked = sorted(
                    zip(self._bm25_index.chunk_ids, scores), key=lambda p: p[1], reverse=True
                )
                for cid, score in ranked[: top_k * BM25_CANDIDATE_MULTIPLIER]:
                    if score > 0:
                        keyword_scores[cid] = float(score)

        candidate_ids = set(vector_scores) | set(keyword_scores)
        if not candidate_ids:
            return []

        norm_vector = _normalize(vector_scores)
        norm_keyword = _normalize(keyword_scores)
        combined = {
            cid: VECTOR_WEIGHT * norm_vector.get(cid, 0.0) + KEYWORD_WEIGHT * norm_keyword.get(cid, 0.0)
            for cid in candidate_ids
        }

        # Need documents/metadatas for any candidate not already returned by the vector query
        # (a BM25-only hit) — fetch everything in one batch by id for simplicity/consistency.
        fetched = self._collection.get(ids=list(candidate_ids), include=["documents", "metadatas"])
        by_id = {
            cid: (doc, meta)
            for cid, doc, meta in zip(fetched["ids"], fetched["documents"], fetched["metadatas"])
        }

        ranked_ids = sorted(combined.items(), key=lambda p: p[1], reverse=True)
        evidence: list[RetrievedEvidence] = []
        for cid, score in ranked_ids:
            if cid not in by_id:
                continue
            document, metadata = by_id[cid]
            if not _matches_where(metadata, where):
                continue
            evidence.append(
                RetrievedEvidence(
                    content=document,
                    scheme_id=metadata["scheme_id"],
                    scheme_name=metadata["scheme_name"],
                    section=metadata["section"],  # type: ignore[arg-type]
                    source=metadata["source"],  # type: ignore[arg-type]
                    source_url=metadata.get("source_url"),
                    policy_version=metadata.get("policy_version"),
                    last_updated=metadata.get("last_updated"),
                    relevance_score=round(score, 4),
                    metadata=metadata,
                )
            )
            if len(evidence) >= top_k:
                break
        return evidence
