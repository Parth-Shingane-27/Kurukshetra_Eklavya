"""Citizen document uploads — deliberately NOT the Document Verification module
(app/modules/document_verification): this is plain document *management*, not verification.
No parsing, no structural checks, no authenticity claim of any kind is made about an uploaded
file — it is accepted, stored, and shown back to the citizen (and an operator/admin acting on
their behalf) purely as their own reference copy, and to auto-mark that document type as
"held" on the profile (Section 13's `CitizenDocument.held`) so the missing-document checklist
reflects it without the citizen re-declaring it separately.
"""

import base64
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.config import get_settings


class DocumentUploadCreate(BaseModel):
    document_type: str
    filename: str
    content_type: str
    file_base64: str

    @field_validator("document_type", "filename", "content_type")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("file_base64")
    @classmethod
    def enforce_size_limit(cls, v: str) -> str:
        try:
            decoded_len = len(base64.b64decode(v, validate=True))
        except Exception as exc:
            raise ValueError("file_base64 is not valid base64") from exc
        if decoded_len == 0:
            raise ValueError("Uploaded file is empty.")
        max_bytes = get_settings().document_upload_max_bytes
        if decoded_len > max_bytes:
            raise ValueError(
                f"File is {decoded_len} bytes, which exceeds the {max_bytes}-byte limit."
            )
        return v


class DocumentUploadOut(BaseModel):
    """Metadata only — never includes `file_base64` (kept out of list views so a listing
    request doesn't pull every file's full content over the wire)."""

    id: str
    citizen_id: str
    document_type: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class DocumentUploadContentOut(BaseModel):
    """Returned only by the single dedicated "download this file" endpoint."""

    id: str
    filename: str
    content_type: str
    file_base64: str
