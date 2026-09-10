from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ActionType, ResourceState, ResourceType


class MockResourceApplyRequest(BaseModel):
    action_id: UUID
    case_id: UUID | None = None
    person_id: UUID
    action_type: ActionType
    resource_type: ResourceType

    resource_key: str = Field(
        min_length=1,
        max_length=160,
    )

    requested_data: dict[str, Any] = Field(
        default_factory=dict
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=120,
    )

    callback_base_url: str | None = None


class MockResourceApplyResponse(BaseModel):
    resource_id: UUID
    resource_key: str
    resource_status: ResourceState
    already_existed: bool


class CompanyResourceResponse(BaseModel):
    id: UUID
    person_id: UUID
    resource_type: ResourceType
    resource_key: str
    status: ResourceState
    details_data: dict[str, Any]
    source_action_id: UUID | None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)