from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_OPERATORS = {"=", "<", "<=", ">", ">=", "in"}


class LinkVerificationStatus(str, Enum):
    """How confidently `SchemeLinks.application_url` (or the absence of one) has been
    established — never inferred from "the URL returned HTTP 200"; only ever set by a human
    curator or an explicit verification step that actually read the destination page.
    """

    verified = "verified"
    """A human (or a verification step whose output a human reviewed) confirmed this is the
    correct, current, official destination for this specific scheme."""
    unverified = "unverified"
    """A URL is present but has not been confirmed — e.g. curator-entered without a
    verification pass, or a verification attempt was inconclusive (fetch blocked, geo-restricted,
    site requires JS rendering we couldn't inspect). Never presented to citizens as "official."""
    not_available = "not_available"
    """Confirmed there is no online self-application for this scheme — e.g. beneficiary
    selection happens via a government survey, or applications only route through an offline/
    in-person process. Distinct from `unverified`: this is a positive finding, not a gap."""
    state_specific = "state_specific"
    """The correct destination depends on the citizen's state/department and no single national
    URL applies — avoid picking one state's portal and presenting it as universal."""


class SchemeLinks(BaseModel):
    """Distinguishes the different official URLs a scheme can have (Section 13 extension) —
    a policy/information page, a scheme's own homepage, the actual application form, a renewal
    portal, and a grievance portal are frequently different destinations and must never be
    conflated into one link."""

    policy_url: str | None = None
    official_scheme_url: str | None = None
    application_url: str | None = None
    renewal_url: str | None = None
    grievance_url: str | None = None
    source_url: str | None = None
    application_link_status: LinkVerificationStatus = LinkVerificationStatus.unverified
    last_verified_at: datetime | None = None
    verification_notes: list[str] = Field(default_factory=list)


class SchemeGuide(BaseModel):
    """FR-014 form-filling guide metadata for one scheme. Steps are plain ordered strings
    rather than free-form markdown/HTML so both the web and mobile catalog screens can render
    them identically. `video_url` is optional and, like `SchemeLinks`, must never be a fabricated
    placeholder — only ever set once a real, checked video walkthrough exists for the scheme."""

    guide_en: list[str] = Field(default_factory=list)
    guide_mr: list[str] = Field(default_factory=list)
    video_url: str | None = None


class SchemeGuideUpdate(BaseModel):
    """All fields optional so an admin/curator can patch just one part of the guide (e.g. add
    a video link later) without clobbering the rest — merged via dot-notation `$set`, same
    pattern as `SchemeLinksUpdate`."""

    guide_en: list[str] | None = None
    guide_mr: list[str] | None = None
    video_url: str | None = None


class SchemeLinksUpdate(BaseModel):
    """All fields optional so PUT /api/schemes/:id can patch a single link field (e.g. just
    re-verify `application_url`) without clobbering the rest of `links` — merged at the storage
    layer via dot-notation `$set`, not a full-document replace (see scheme_kb/service.py)."""

    policy_url: str | None = None
    official_scheme_url: str | None = None
    application_url: str | None = None
    renewal_url: str | None = None
    grievance_url: str | None = None
    source_url: str | None = None
    application_link_status: LinkVerificationStatus | None = None
    last_verified_at: datetime | None = None
    verification_notes: list[str] | None = None


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
    links: SchemeLinks = Field(default_factory=SchemeLinks)
    """Replaces the earlier flat `source_reference`/`application_link` strings (migrated) —
    see `SchemeLinks` for why a scheme's policy page, official homepage, application form,
    renewal portal, and grievance portal must be tracked separately rather than as one URL."""
    guide: SchemeGuide | None = None
    """FR-014: optional form-filling guide (English/Marathi steps, video link). None means no
    guide has been authored for this scheme yet — the catalog shows that honestly rather than
    inventing generic filler steps."""
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
    links: SchemeLinksUpdate | None = None
    guide: SchemeGuideUpdate | None = None
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
