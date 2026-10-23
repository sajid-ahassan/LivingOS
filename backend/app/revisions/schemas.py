from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ApprovalState, PlanState
from app.planning.schemas import GeneratedCasePlan


class PlanRevisionRequest(BaseModel):
    plan_data: GeneratedCasePlan
    correction_summary: str = Field(min_length=10, max_length=1000)


class PlanRevisionResponse(BaseModel):
    id: UUID
    case_id: UUID
    revision: int
    status: PlanState
    summary: str
    plan_data: dict
    parent_plan_id: UUID
    correction_summary: str
    approval_id: UUID
    approval_status: ApprovalState
    assigned_to: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
