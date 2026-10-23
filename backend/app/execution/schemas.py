from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums import (
    ActionState,
    ActionType,
    CaseState,
    ResourceType,
)


class ActionExecutionResponse(BaseModel):
    id: UUID
    action_type: ActionType
    resource_type: ResourceType
    status: ActionState
    attempt_count: int
    result_data: dict[str, Any] | None
    verification_data: dict[str, Any] | None
    error_message: str | None

    model_config = ConfigDict(
        from_attributes=True
    )


class PlanExecutionResponse(BaseModel):
    plan_id: UUID
    case_id: UUID
    case_status: CaseState
    actions: list[ActionExecutionResponse]