from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.bundle import BundleOut, ConflictDetectResponse
from app.models.checklist import ChecklistResponse
from app.models.eligibility import EvaluateResponse


class RunPipelineRequest(BaseModel):
    citizen_id: str


class RunPipelineResponse(BaseModel):
    citizen_id: str
    eligibility: EvaluateResponse
    conflicts: ConflictDetectResponse
    bundle: BundleOut
    checklist: ChecklistResponse


class TraceStep(BaseModel):
    step_name: str
    input_snapshot: dict[str, Any]
    output_snapshot: dict[str, Any]
    created_at: datetime


class TraceResponse(BaseModel):
    citizen_id: str
    steps: list[TraceStep]
