from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import check_owner_or_public, get_current_user_optional
from app.core.db import get_db
from app.models.document_upload import DocumentUploadContentOut, DocumentUploadCreate, DocumentUploadOut
from app.modules.document_uploads import service

router = APIRouter(prefix="/api/citizens/{citizen_id}/document-uploads", tags=["document-uploads"])


@router.post("", response_model=DocumentUploadOut, status_code=201)
async def upload_document(
    citizen_id: str,
    payload: DocumentUploadCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.upload_document(db, citizen_id, payload)


@router.get("", response_model=list[DocumentUploadOut])
async def list_documents(
    citizen_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.list_documents(db, citizen_id)


@router.get("/{upload_id}/content", response_model=DocumentUploadContentOut)
async def get_document_content(
    citizen_id: str,
    upload_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    return await service.get_document_content(db, citizen_id, upload_id)


@router.delete("/{upload_id}", status_code=204)
async def delete_document(
    citizen_id: str,
    upload_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    await check_owner_or_public(db, citizen_id, current_user)
    await service.delete_document(db, citizen_id, upload_id)
