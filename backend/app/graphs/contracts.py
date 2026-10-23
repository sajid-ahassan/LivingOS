from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ResourceType


class BaseGraphState(TypedDict, total=False):
    correlation_id: str
    case_id: str
    case_facts: dict[str, Any]
    resources: list[dict[str, Any]]
    retrieval: dict[str, Any]
    draft: dict[str, Any]
    validation_errors: list[str]
    repair_count: int
    final_output: dict[str, Any]
    terminal_state: str


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    reason: str


class PlannedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: ResourceType
    catalog_key: str
    level: str | None = None
    reason: str = Field(max_length=500)
    evidence_refs: list[EvidenceRef]
    requires_it_approval: bool = False


class OnboardingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment: list[PlannedItem]
    accounts: list[PlannedItem]
    access: list[PlannedItem]
    training: list[PlannedItem]
    restrictions: list[str]
    confidence: float = Field(ge=0, le=1)
    needs_human_review: bool
    review_reason: str | None = None
