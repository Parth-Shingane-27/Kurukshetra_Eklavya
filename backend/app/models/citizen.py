from datetime import date, datetime

from pydantic import BaseModel, Field


class CitizenDocument(BaseModel):
    """A document type the citizen has declared as held (or not)."""

    document_type: str
    held: bool


class CitizenBase(BaseModel):
    name: str
    date_of_birth: date
    state: str
    district: str
    gender: str | None = None
    annual_income: float | None = None
    occupation: str | None = None
    social_category: str | None = None
    disability_status: bool | None = None
    land_holding_acres: float | None = None
    family_size: int | None = None
    marital_status: str | None = None
    bpl_status: bool | None = None
    education_level: str | None = None
    employment_status: str | None = None
    documents: list[CitizenDocument] = Field(default_factory=list)


class CitizenCreate(CitizenBase):
    pass


class CitizenUpdate(BaseModel):
    """All fields optional — only provided fields are patched (FR-002)."""

    name: str | None = None
    date_of_birth: date | None = None
    state: str | None = None
    district: str | None = None
    gender: str | None = None
    annual_income: float | None = None
    occupation: str | None = None
    social_category: str | None = None
    disability_status: bool | None = None
    land_holding_acres: float | None = None
    family_size: int | None = None
    marital_status: str | None = None
    bpl_status: bool | None = None
    education_level: str | None = None
    employment_status: str | None = None


class DocumentsDeclare(BaseModel):
    """Full replacement of the citizen's held-documents list (FR-001 'declare documents')."""

    documents: list[CitizenDocument]


class CitizenOut(CitizenBase):
    id: str
    created_at: datetime
    updated_at: datetime
