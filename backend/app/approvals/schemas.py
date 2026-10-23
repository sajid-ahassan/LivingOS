from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ApprovalState, ApprovalTargetType


class PlanSubmissionRequest(BaseModel):
    assigned_to: UUID


class ApprovalResponse(BaseModel):
    id: UUID
    target_type: ApprovalTargetType
    target_id: UUID
    requested_by: UUID
    assigned_to: UUID
    status: ApprovalState
    comment: str | None
    requested_at: datetime
    decided_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalDecisionRequest(BaseModel):
    decided_by: UUID
    decision: Literal[
        ApprovalState.APPROVED,
        ApprovalState.REJECTED,
    ]
    comment: str | None = Field(default=None, max_length=1000)
