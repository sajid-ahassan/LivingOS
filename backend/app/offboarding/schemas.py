from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import PlanState, ResourceState, ResourceType
from app.planning.schemas import PlannedAction


class OffboardingResourceInventoryItem(BaseModel):
    resource_type: ResourceType
    resource_key: str
    status: ResourceState
    owner_id: UUID
    title: str | None = None
    due_date: str | None = None


class OffboardingNotification(BaseModel):
    audience: str = Field(min_length=2, max_length=80)
    reason: str = Field(min_length=5, max_length=300)
    evidence_ids: list[str] = Field(min_length=1)


class OffboardingPlan(BaseModel):
    summary: str = Field(min_length=10, max_length=1000)
    revocations: list[PlannedAction] = Field(default_factory=list)
    asset_returns: list[PlannedAction] = Field(default_factory=list)
    reassignments: list[PlannedAction] = Field(default_factory=list)
    notifications: list[OffboardingNotification] = Field(default_factory=list)
    handover_topics: list[str] = Field(default_factory=list, max_length=12)
    targeted_questions: list[str] = Field(default_factory=list, max_length=12)
    evidence_refs: list[str] = Field(default_factory=list)
    needs_human_review: bool = False

    model_config = ConfigDict(extra="forbid")


class OffboardingPlanResponse(BaseModel):
    id: UUID
    case_id: UUID
    revision: int
    status: PlanState
    summary: str
    plan_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
