from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import CasePriority, CaseState, CaseType


class CaseCreateRequest(BaseModel):
    case_type: CaseType
    subject_person_id: UUID
    created_by_id: UUID
    priority: CasePriority = CasePriority.NORMAL
    case_facts: dict[str, Any] = Field(default_factory=dict)


class CaseResponse(BaseModel):
    id: UUID
    case_type: CaseType
    subject_person_id: UUID
    created_by_id: UUID
    status: CaseState
    priority: CasePriority
    case_facts: dict[str, Any]
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class CaseTriageResponse(BaseModel):
    case_id: UUID
    ready_for_planning: bool
    missing_fields: list[str]
    previous_status: CaseState
    current_status: CaseState




class PolicyEvidenceResponse(BaseModel):
    evidence_id: str
    policy_code: str
    version_number: int
    text: str
    score: float


class CasePolicyContextResponse(BaseModel):
    case_id: UUID
    search_query: str
    evidence: list[PolicyEvidenceResponse]