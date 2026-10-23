from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    ApprovalState,
    CaseType,
    LearningState,
    LearningTriggerType,
)


class LearningCandidate(BaseModel):
    situation: str = Field(min_length=10, max_length=1000)
    conditions: list[str] = Field(default_factory=list, max_length=12)
    recommended_action: str = Field(min_length=10, max_length=1000)
    rationale: str = Field(min_length=10, max_length=1500)
    scope: dict[str, list[str] | str]
    policy_refs: list[str] = Field(default_factory=list)
    source_evidence: list[str] = Field(default_factory=list)
    sensitive_data_removed: bool
    confidence: float = Field(ge=0, le=1)


class LearningCandidateCreateRequest(BaseModel):
    assigned_to: UUID


class LearningCandidateCreateResponse(BaseModel):
    learning_record_id: UUID
    approval_id: UUID
    source_case_id: UUID
    source_plan_id: UUID
    trigger_type: LearningTriggerType
    learning_status: LearningState
    approval_status: ApprovalState
    candidate: LearningCandidate
    duplicate_warning: bool = False


class LearningDecisionRequest(BaseModel):
    decided_by: UUID
    decision: ApprovalState
    comment: str | None = Field(default=None, max_length=1000)


class LearningDecisionResponse(BaseModel):
    approval_id: UUID
    learning_record_id: UUID
    approval_status: ApprovalState
    learning_status: LearningState
    qdrant_point_id: UUID | None = None
    comment: str | None = None
    decided_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LearningIndexResponse(BaseModel):
    learning_record_id: UUID
    status: LearningState
    qdrant_point_id: UUID
    evidence_id: str
    sanitized_before_indexing: bool
    policy_version_ids: list[UUID] = Field(default_factory=list)


class LearningSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1200)
    case_type: CaseType
    department: str = Field(min_length=1, max_length=80)
    role: str | None = Field(default=None, max_length=120)
    sensitivity: str | None = Field(default=None, max_length=40)
    top_k: int = Field(default=2, ge=1, le=6)


class LearningEvidence(BaseModel):
    evidence_id: str
    learning_id: UUID
    trigger_type: LearningTriggerType
    text: str
    score: float
    policy_version_ids: list[UUID] = Field(default_factory=list)
    scope: dict = Field(default_factory=dict)


class LearningSearchResponse(BaseModel):
    query: str
    results: list[LearningEvidence]
