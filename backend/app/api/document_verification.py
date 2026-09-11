from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.models.document_verification import DocumentVerificationOut, DocumentVerifyRequest
from app.modules.document_verification import service

router = APIRouter(prefix="/api/documents", tags=["document-verification"])


@router.post("/verify", response_model=DocumentVerificationOut, status_code=201)
async def verify_document(payload: DocumentVerifyRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.verify_document_for_citizen(
        db,
        citizen_id=payload.citizen_id,
        scheme_id=payload.scheme_id,
        document_type=payload.document_type,
        pdf_base64=payload.pdf_base64,
        document_text=payload.document_text,
        declared_fields=payload.declared_fields,
    )


@router.get("/verify/{verification_id}", response_model=DocumentVerificationOut)
async def get_verification(verification_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.get_document_verification(db, verification_id)


@router.get("/verify/citizen/{citizen_id}", response_model=list[DocumentVerificationOut])
async def list_verifications_for_citizen(citizen_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_document_verifications_for_citizen(db, citizen_id)
