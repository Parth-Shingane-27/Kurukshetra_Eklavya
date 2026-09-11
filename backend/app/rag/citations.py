"""Best-effort evidence attachment for the Explanation and Checklist agents (Section 6 of
the brief: "Explanation Agent should be able to say... which source supports the result").

Mirrors the existing BR-010 pattern in `explanation/service.py` exactly: skip entirely when no
`GEMINI_API_KEY` is configured (matches the existing "optional LLM step" convention — RAG
citation attachment is an enhancement, not a requirement, for these two already-deterministic
agents), and never let a retrieval failure break the pipeline. Because it's skipped whenever
no key is configured, this also means the existing test suite (which runs with no real key)
never touches the vector store, keeping those tests side-effect-free.
"""

import logging

from app.core.config import get_settings
from app.rag.policy_service import get_policy_service

logger = logging.getLogger(__name__)

CITATION_TOP_K = 1


async def attach_policy_citations(included: list[dict]) -> list[dict] | None:
    """For each bundle-included scheme, best-effort one supporting evidence snippet by
    scheme-name match against the policy corpus. Returns None (not an empty list) when
    skipped/unavailable, so callers can tell "not attempted" apart from "attempted, found
    nothing" if that distinction ever matters."""
    settings = get_settings()
    if not settings.gemini_api_key or not included:
        return None
    try:
        service = get_policy_service()
        citations = []
        for scheme in included:
            result = await service.retrieve_policy_evidence(scheme["scheme_name"], top_k=CITATION_TOP_K)
            if result.verified:
                citations.append(
                    {
                        "scheme_id": scheme["scheme_id"],
                        "scheme_name": scheme["scheme_name"],
                        "evidence": [e.model_dump() for e in result.evidence],
                    }
                )
        return citations or None
    except Exception:
        logger.warning("Policy citation attachment failed; bundle proceeds without it.", exc_info=True)
        return None


async def attach_document_evidence(checklist_items: list[dict]) -> list[dict]:
    """Best-effort per-item `evidence` (Section 6: Checklist Agent "retrieve scheme-specific
    document requirements... grounded in the retrieved data"). Items are returned unchanged
    (no `evidence` key added) when skipped or nothing matches — never fabricated."""
    settings = get_settings()
    if not settings.gemini_api_key or not checklist_items:
        return checklist_items
    try:
        service = get_policy_service()
        enriched = []
        for item in checklist_items:
            result = await service.retrieve_policy_evidence(
                f"{item['document_type']} document requirement", top_k=CITATION_TOP_K
            )
            item = dict(item)
            if result.verified:
                item["evidence"] = [e.model_dump() for e in result.evidence]
            enriched.append(item)
        return enriched
    except Exception:
        logger.warning("Checklist evidence attachment failed; checklist proceeds without it.", exc_info=True)
        return checklist_items
