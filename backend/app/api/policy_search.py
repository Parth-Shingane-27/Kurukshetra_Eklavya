"""Thin HTTP surface over the Shared Policy Knowledge Service (Section 4/14 of the brief) —
"example retrieval results" you can curl directly, and the endpoint the Scheme Knowledge Base
Agent uses for discovery across the full 3,397-scheme corpus (distinct from the curated,
Rule-Engine-backed `/api/schemes` catalogue, which is untouched by this router).
"""

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.rag.policy_service import PolicyKnowledgeService, get_policy_service
from app.rag.schemas import RetrievalResult

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.get("/search", response_model=RetrievalResult)
async def search_policy(
    q: str = Query(..., min_length=1),
    scheme_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    level: str | None = Query(default=None),
    service: PolicyKnowledgeService = Depends(get_policy_service),
):
    filters = {k: v for k, v in {"scheme_id": scheme_id, "category": category, "level": level}.items() if v}
    return await service.retrieve_policy_evidence(q, filters=filters or None)


@router.get("/schemes/{scheme_id}/eligibility", response_model=RetrievalResult)
async def scheme_eligibility(
    scheme_id: str,
    service: PolicyKnowledgeService = Depends(get_policy_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.retrieve_eligibility_rules(scheme_id, db=db)


@router.get("/schemes/{scheme_id}/documents", response_model=RetrievalResult)
async def scheme_documents(
    scheme_id: str,
    service: PolicyKnowledgeService = Depends(get_policy_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.retrieve_required_documents(scheme_id, db=db)


@router.get("/schemes/{scheme_id}/deadlines", response_model=RetrievalResult)
async def scheme_deadlines(
    scheme_id: str,
    service: PolicyKnowledgeService = Depends(get_policy_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.retrieve_deadlines(scheme_id, db=db)


@router.get("/grievance", response_model=RetrievalResult)
async def grievance_procedure(
    scheme_id: str | None = Query(default=None),
    service: PolicyKnowledgeService = Depends(get_policy_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await service.retrieve_grievance_procedure(scheme_id=scheme_id, db=db)
