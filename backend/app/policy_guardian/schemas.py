from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    ApprovalState,
    ImpactRecommendedAction,
    ImpactState,
    PlanState,
    PolicyChangeState,
    PolicyImpactTargetType,
    PolicyState,
    RiskLevel,
)


class GuardianChangeSummary(BaseModel):
    added_rules: list[str] = Field(default_factory=list, max_length=20)
    removed_rules: list[str] = Field(default_factory=list, max_length=20)
    modified_rules: list[str] = Field(default_factory=list, max_length=20)
    affected_areas: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(min_length=5, max_length=2000)
    overall_risk: RiskLevel


class PolicyActivateRequest(BaseModel):
    policy_code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=180)
    version_number: int = Field(ge=2)
    department: str = Field(min_length=2, max_length=80)
    effective_from: date
    uploaded_by: UUID
    content_text: str = Field(min_length=40)


class PolicyVersionRead(BaseModel):
    id: UUID
    policy_code: str
    title: str
    version_number: int
    status: PolicyState
    department: str
    effective_from: date

    model_config = ConfigDict(from_attributes=True)


class PolicyImpactRead(BaseModel):
    id: UUID
    policy_change_id: UUID
    target_type: PolicyImpactTargetType
    target_id: UUID
    risk_level: RiskLevel
    explanation: str
    recommended_action: ImpactRecommendedAction
    status: ImpactState
    resolved_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyChangeRead(BaseModel):
    id: UUID
    policy_code: str
    old_version_id: UUID
    new_version_id: UUID
    diff_data: dict
    overall_risk: RiskLevel
    status: PolicyChangeState
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyActivationResponse(BaseModel):
    old_version: PolicyVersionRead
    new_version: PolicyVersionRead
    policy_change: PolicyChangeRead
    impacts: list[PolicyImpactRead]
    stale_learning_ids: list[UUID] = Field(default_factory=list)
    paused_case_ids: list[UUID] = Field(default_factory=list)
    human_review_case_ids: list[UUID] = Field(default_factory=list)
    indexed_chunks: int


class PolicyChangeDetailResponse(BaseModel):
    change: PolicyChangeRead
    impacts: list[PolicyImpactRead]


class RegenerateImpactRequest(BaseModel):
    resolved_by: UUID
    comment: str = Field(min_length=5, max_length=1000)


class RegenerateImpactResponse(BaseModel):
    impact_id: UUID
    impact_status: ImpactState
    stale_plan_id: UUID
    stale_plan_status: PlanState
    new_plan_id: UUID
    new_revision: int
    new_plan_status: PlanState
    approval_id: UUID
    approval_status: ApprovalState
    assigned_to: UUID
    case_id: UUID
    case_status: str
    evidence_ids: list[str]


class ResourceRemediationRequest(BaseModel):
    requested_by: UUID


class ResourceRemediationResponse(BaseModel):
    impact_id: UUID
    impact_status: ImpactState
    case_id: UUID
    plan_id: UUID
    approval_id: UUID
    assigned_to: UUID


class ResourceRecertifyRequest(BaseModel):
    decided_by: UUID


class ResourceRecertifyResponse(BaseModel):
    impact_id: UUID
    impact_status: ImpactState
    resource_key: str
    sponsor_id: UUID
