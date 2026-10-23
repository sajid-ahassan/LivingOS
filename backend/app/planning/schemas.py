from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    ActionType,
    PlanState,
    ResourceType,
)


class PlannedAction(BaseModel):
    sequence: int = Field(ge=1)
    action_type: ActionType
    resource_type: ResourceType

    resource_key: str = Field(
        min_length=1,
        max_length=160,
    )

    requested_data: dict[str, Any] = Field(
        default_factory=dict
    )

    reason: str = Field(
        min_length=5,
        max_length=500,
    )

    evidence_ids: list[str] = Field(
        min_length=1,
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class GeneratedCasePlan(BaseModel):
    summary: str = Field(
        min_length=10,
        max_length=1000,
    )

    actions: list[PlannedAction] = Field(
        min_length=1,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class CasePlanResponse(BaseModel):
    id: UUID
    case_id: UUID
    revision: int
    status: PlanState
    summary: str | None
    plan_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
