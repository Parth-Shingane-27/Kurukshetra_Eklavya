from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_OPERATORS = {"=", "<", "<=", ">", ">=", "in"}


class SchemeRule(BaseModel):
    """One eligibility condition belonging to a scheme (Section 13).

    Validated at parse time (FR-011: "invalid rule syntax -> validation error, entry
    rejected") so FastAPI/pydantic reject a malformed rule with a 422 before any handler
    code runs, for every endpoint that accepts a Scheme, not just the admin-only ones.
    """

    field_name: str
    operator: str  # "=", "<", "<=", ">", ">=", "in"
    value: Any
    logical_group: str | None = None

    @field_validator("field_name")
    @classmethod
    def field_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field_name must not be blank")
        return v

    @field_validator("operator")
    @classmethod
    def operator_must_be_supported(cls, v: str) -> str:
        if v not in ALLOWED_OPERATORS:
            raise ValueError(f"operator must be one of {sorted(ALLOWED_OPERATORS)}, got {v!r}")
        return v

    @model_validator(mode="after")
    def value_shape_matches_operator(self) -> "SchemeRule":
        if self.operator == "in" and not isinstance(self.value, list):
            raise ValueError("operator 'in' requires a list value")
        if self.operator != "in" and isinstance(self.value, list):
            raise ValueError(f"operator {self.operator!r} does not accept a list value")
        return self


class SchemeDocumentRequirement(BaseModel):
    document_type: str
    is_mandatory: bool = True

    @field_validator("document_type")
    @classmethod
    def document_type_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("document_type must not be blank")
        return v


class SchemeBase(BaseModel):
    name: str
    description: str | None = None
    issuing_authority: str | None = None
    category: str
    benefit_type: str
    benefit_value_estimate: float
    conflict_group: str | None = None
    is_active: bool = True
    source_reference: str | None = None
    application_link: str | None = None
    """Official government registration/application form URL for this scheme — distinct from
    `source_reference` (a general citation/source), this is specifically where a citizen goes
    to apply. Curated manually for now (see plan.md FR-014/FR-015 for the eventual automated
    freshness layer)."""
    rules: list[SchemeRule] = Field(default_factory=list)
    document_requirements: list[SchemeDocumentRequirement] = Field(default_factory=list)


class SchemeCreate(SchemeBase):
    pass


class SchemeUpdate(BaseModel):
    """All fields optional — only provided fields are patched. Also how a scheme is
    deactivated: PUT with {"is_active": false} (BR-003 then excludes it from evaluation)."""

    name: str | None = None
    description: str | None = None
    issuing_authority: str | None = None
    category: str | None = None
    benefit_type: str | None = None
    benefit_value_estimate: float | None = None
    conflict_group: str | None = None
    is_active: bool | None = None
    source_reference: str | None = None
    application_link: str | None = None
    rules: list[SchemeRule] | None = None
    document_requirements: list[SchemeDocumentRequirement] | None = None


class SchemeOut(SchemeBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ConflictRuleCreate(BaseModel):
    """FR-011's "conflict declaration" — the BR-004 direct-pairwise mechanism, distinct from
    a scheme's own `conflict_group` string (BR-005). A separate collection since it links two
    independent scheme documents (Section 13)."""

    scheme_a_id: str
    scheme_b_id: str
    conflict_type: str = "mutually_exclusive"
    reason: str | None = None

    @field_validator("conflict_type")
    @classmethod
    def conflict_type_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("conflict_type must not be blank")
        return v

    @model_validator(mode="after")
    def schemes_must_differ(self) -> "ConflictRuleCreate":
        if self.scheme_a_id == self.scheme_b_id:
            raise ValueError("scheme_a_id and scheme_b_id must be different schemes")
        return self


class ConflictRuleOut(BaseModel):
    id: str
    scheme_a_id: str
    scheme_a_name: str
    scheme_b_id: str
    scheme_b_name: str
    conflict_type: str
    reason: str | None = None
