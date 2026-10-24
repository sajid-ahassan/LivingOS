from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.enums import AppRole, EmploymentStatus, ResourceState


class AgentSponsor(BaseModel):
    id: UUID
    name: str
    department: str | None
    employment_status: EmploymentStatus


class AgentSummary(BaseModel):
    resource_key: str
    agent_name: str | None
    platform: str | None
    purpose: str | None
    scopes: list[dict[str, Any]]
    risk_tier: str | None
    status: ResourceState
    credential_key: str | None
    expires_at: str | None
    last_active_at: str | None
    sponsor_id: UUID
    sponsor: AgentSponsor | None
    orphan: bool
    orphan_reasons: list[str]


class AgentCredential(BaseModel):
    resource_key: str
    status: ResourceState
    sponsor_id: UUID
    kind: str | None
    permission: str | None
    details: dict[str, Any]


class PersonNode(BaseModel):
    id: UUID
    name: str
    department: str | None
    job_title: str | None
    app_role: AppRole
    employment_status: EmploymentStatus
    access_count: int


class AgentNode(BaseModel):
    resource_key: str
    agent_name: str | None
    sponsor_id: UUID
    department: str | None
    risk_tier: str | None
    status: ResourceState
    orphan: bool
    orphan_reasons: list[str]
    # An open Policy Guardian impact on the agent or its credential.
    policy_violation: bool = False


class WorkforceEdge(BaseModel):
    source: str
    target: str
    kind: Literal["MANAGER", "SPONSOR"]


class WorkforceGraph(BaseModel):
    people: list[PersonNode]
    agents: list[AgentNode]
    edges: list[WorkforceEdge]
