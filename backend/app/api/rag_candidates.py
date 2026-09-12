from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.rag_candidate import RagCandidateOut, RagCandidateRejectRequest
from app.modules.rag_refresh import service

router = APIRouter(prefix="/api/admin", tags=["rag-candidates"], dependencies=[Depends(require_admin)])


@router.post("/rag/refresh")
async def refresh_scheme(scheme_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    candidate = await service.refresh_scheme_candidate(db, scheme_id)
    if candidate is None:
        return {"candidate": None, "message": "No confident candidate update could be produced for this scheme."}
    return {"candidate": candidate, "message": None}


@router.get("/rag-candidates", response_model=list[RagCandidateOut])
async def list_candidates(status: str | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_candidates(db, status=status)


@router.get("/rag-candidates/{candidate_id}", response_model=RagCandidateOut)
async def get_candidate(candidate_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_candidate(db, candidate_id)


@router.post("/rag-candidates/{candidate_id}/approve", response_model=RagCandidateOut)
async def approve_candidate(candidate_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.approve_candidate(db, candidate_id)


@router.post("/rag-candidates/{candidate_id}/reject", response_model=RagCandidateOut)
async def reject_candidate(
    candidate_id: str, payload: RagCandidateRejectRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    return await service.reject_candidate(db, candidate_id, reason=payload.reason)
