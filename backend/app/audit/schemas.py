from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import AuditActorType


class AuditEventRead(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_type: AuditActorType
    actor_id: UUID | None = None
    event_type: str
    entity_type: str
    entity_id: UUID
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    evidence_data: dict[str, Any] | None = None
    correlation_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CaseAuditTimelineResponse(BaseModel):
    case_id: UUID
    total_events: int
    event_types: list[str] = Field(default_factory=list)
    events: list[AuditEventRead]


class AuditCoverageResponse(BaseModel):
    case_id: UUID
    total_events: int
    present_groups: dict[str, bool]
    missing_groups: list[str]
    complete_for_current_case_state: bool
