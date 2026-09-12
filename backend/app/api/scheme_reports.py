from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import require_admin
from app.core.db import get_db
from app.models.scheme_report import ResolveSchemeReportRequest, SchemeReportCreate, SchemeReportOut
from app.modules.scheme_reports import service

router = APIRouter(prefix="/api/scheme-reports", tags=["scheme-reports"])


@router.post("", response_model=SchemeReportOut, status_code=201)
async def create_report(payload: SchemeReportCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.create_report(db, payload.scheme_id, payload.reason, payload.comment, payload.citizen_id)


@router.get("", response_model=list[SchemeReportOut], dependencies=[Depends(require_admin)])
async def list_reports(status: str | None = Query(default=None), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.list_reports(db, status=status)


@router.post("/{report_id}/resolve", response_model=SchemeReportOut, dependencies=[Depends(require_admin)])
async def resolve_report(report_id: str, payload: ResolveSchemeReportRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.resolve_report(db, report_id, payload.status.value, payload.admin_notes)
