from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.access_requests.auth import AgentAuthError, authenticate_agent, check_service_token
from app.access_requests.service import (
    AccessRequestError,
    AccessRequestInput,
    AccessRequestNotFoundError,
    agent_grants,
    create_access_request,
    expire_due_grants,
    release_grant,
    request_status,
)
from app.agents.service import build_agent_summary
from app.agents.schemas import AgentSummary
from app.config import get_settings
from app.database import get_db
from app.models import CompanyResource, Person


router = APIRouter(tags=["access-requests"])


class AccessRequestBody(BaseModel):
    system: str = Field(default="github", min_length=2, max_length=40)
    resource: str = Field(min_length=1, max_length=120)
    permission: str = Field(min_length=2, max_length=20)
    duration_minutes: int = Field(ge=1, le=7 * 24 * 60)
    reason: str = Field(min_length=5, max_length=500)


class AccessRequestStatus(BaseModel):
    request_id: UUID
    state: str
    tier: str | None
    tier_reasons: list[str]
    approver_note: str | None
    grant_key: str | None
    expires_at: str | None
    detail: str | None


class GrantView(BaseModel):
    resource_key: str
    status: str
    permission: str | None
    repository: str | None
    expires_at: str | None
    temporary: bool


class ExpireDueResponse(BaseModel):
    expired: list[str]


def _agent(db: Session, key: str | None) -> CompanyResource:
    try:
        return authenticate_agent(db, key)
    except AgentAuthError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error


def _http(error: AccessRequestError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(error, AccessRequestNotFoundError)
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(code, str(error))


def _grant_view(grant: CompanyResource) -> GrantView:
    details: dict[str, Any] = grant.details_data or {}
    return GrantView(
        resource_key=grant.resource_key,
        status=grant.status.value,
        permission=details.get("permission"),
        repository=details.get("repository"),
        expires_at=details.get("expires_at"),
        temporary=details.get("kind") == "temporary_grant",
    )


@router.get("/agent-identity", response_model=AgentSummary)
def whoami(
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AgentSummary:
    """MCP `whoami`: the calling agent, its sponsor and orphan status."""
    agent = _agent(db, x_agent_key)
    return build_agent_summary(
        agent, db.get(Person, agent.person_id), datetime.now(timezone.utc)
    )


@router.post(
    "/access-requests",
    response_model=AccessRequestStatus,
    status_code=status.HTTP_201_CREATED,
)
def request_access(
    body: AccessRequestBody,
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccessRequestStatus:
    """MCP `request_access`: tiered by rules; LOW runs at once, HIGH waits."""
    agent = _agent(db, x_agent_key)
    try:
        case = create_access_request(db, agent, AccessRequestInput(**body.model_dump()))
        return AccessRequestStatus(**request_status(db, agent, case.id))
    except AccessRequestError as error:
        raise _http(error) from error


@router.get("/access-requests/{request_id}", response_model=AccessRequestStatus)
def check_request(
    request_id: UUID,
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccessRequestStatus:
    """MCP `check_request`."""
    agent = _agent(db, x_agent_key)
    try:
        return AccessRequestStatus(**request_status(db, agent, request_id))
    except AccessRequestError as error:
        raise _http(error) from error


@router.get("/access-grants/mine", response_model=list[GrantView])
def list_my_access(
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> list[GrantView]:
    """MCP `list_my_access`: the agent's credentials and grants with expiry."""
    agent = _agent(db, x_agent_key)
    return [_grant_view(grant) for grant in agent_grants(db, agent)]


@router.post("/access-grants/{grant_key}/release", response_model=AccessRequestStatus)
def release_access(
    grant_key: str,
    x_agent_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AccessRequestStatus:
    """MCP `release_access`: the agent gives its temporary access back early."""
    agent = _agent(db, x_agent_key)
    try:
        case = release_grant(db, agent, grant_key)
        return AccessRequestStatus(**request_status(db, agent, case.id))
    except AccessRequestError as error:
        raise _http(error) from error


@router.post("/access-grants/expire-due", response_model=ExpireDueResponse)
def expire_due(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ExpireDueResponse:
    """Called by the n8n expiry sweeper with the service token."""
    try:
        check_service_token(authorization, get_settings().mcp_service_token)
    except AgentAuthError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
    return ExpireDueResponse(expired=expire_due_grants(db))
