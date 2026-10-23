from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ApprovalState, LearningState


class HandoverGenerateRequest(BaseModel):
    assigned_to: UUID
    answers: dict[str, str] = Field(default_factory=dict)


class HandoverDocument(BaseModel):
    summary: str = Field(min_length=20, max_length=1500)
    ongoing_work: list[str] = Field(default_factory=list, max_length=12)
    recurring_tasks: list[str] = Field(default_factory=list, max_length=12)
    known_issues: list[str] = Field(default_factory=list, max_length=12)
    key_contacts: list[str] = Field(default_factory=list, max_length=12)
    undocumented_procedures: list[str] = Field(default_factory=list, max_length=12)
    successor_notes: list[str] = Field(default_factory=list, max_length=12)
    sensitive_data_removed: bool


class HandoverGenerateResponse(BaseModel):
    learning_record_id: UUID
    approval_id: UUID
    case_id: UUID
    plan_id: UUID
    status: LearningState
    approval_status: ApprovalState
    handover: HandoverDocument


class HandoverDecisionRequest(BaseModel):
    decided_by: UUID
    decision: ApprovalState
    comment: str | None = Field(default=None, max_length=1000)


class HandoverDecisionResponse(BaseModel):
    approval_id: UUID
    learning_record_id: UUID
    approval_status: ApprovalState
    learning_status: LearningState
    comment: str | None
    decided_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
