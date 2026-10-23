from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import AlertState


class AccessEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    event_time: datetime
    source: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=40)
    success: bool


class AccessEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    event_time: datetime
    source: str
    destination: str
    event_type: str
    success: bool
    features_data: dict
    anomaly_score: float
    alert_status: AlertState
    reviewed_by: UUID | None = None
    review_comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlertReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_by: UUID
    decision: AlertState
    comment: str | None = Field(default=None, max_length=1000)


class SecurityAlertListItem(AccessEventRead):
    pass
