"""Read-only views of AI agents and the workforce map.

Agents are CompanyResource rows (AI_AGENT) whose person_id is the human
sponsor. Orphan status always comes from the deterministic rules in
agents/rules.py, never from an LLM.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.rules import orphan_reasons
from app.agents.schemas import (
    AgentCredential,
    AgentNode,
    AgentSponsor,
    AgentSummary,
    PersonNode,
    WorkforceEdge,
    WorkforceGraph,
)
from app.enums import ResourceType
from app.models import CompanyResource, Person
from app.offboarding.rules import TERMINAL_RESOURCE_STATES
from app.resource_rules import AGENT_RESOURCE_TYPES


class AgentNotFoundError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_agent_summary(
    agent: CompanyResource,
    sponsor: Person | None,
    now: datetime,
) -> AgentSummary:
    details = agent.details_data or {}
    reasons = orphan_reasons(agent, sponsor, now)
    return AgentSummary(
        resource_key=agent.resource_key,
        agent_name=details.get("agent_name"),
        platform=details.get("platform"),
        purpose=details.get("purpose"),
        scopes=list(details.get("scopes") or []),
        risk_tier=details.get("risk_tier"),
        status=agent.status,
        credential_key=details.get("credential_key"),
        expires_at=details.get("expires_at"),
        last_active_at=details.get("last_active_at"),
        sponsor_id=agent.person_id,
        sponsor=(
            AgentSponsor(
                id=sponsor.id,
                name=sponsor.name,
                department=sponsor.department,
                employment_status=sponsor.employment_status,
            )
            if sponsor is not None
            else None
        ),
        orphan=bool(reasons),
        orphan_reasons=reasons,
    )


def build_credential(resource: CompanyResource) -> AgentCredential:
    details = dict(resource.details_data or {})
    return AgentCredential(
        resource_key=resource.resource_key,
        status=resource.status,
        sponsor_id=resource.person_id,
        kind=details.get("kind"),
        permission=details.get("permission"),
        details=details,
    )


def build_workforce_graph(
    people: Iterable[Person],
    resources: Iterable[CompanyResource],
    now: datetime,
) -> WorkforceGraph:
    people = list(people)
    resources = list(resources)
    people_by_id = {person.id: person for person in people}

    access_counts: dict[UUID, int] = {}
    agents: list[AgentNode] = []
    edges: list[WorkforceEdge] = []

    for resource in resources:
        if resource.resource_type == ResourceType.AI_AGENT:
            sponsor = people_by_id.get(resource.person_id)
            reasons = orphan_reasons(resource, sponsor, now)
            details = resource.details_data or {}
            agents.append(
                AgentNode(
                    resource_key=resource.resource_key,
                    agent_name=details.get("agent_name"),
                    sponsor_id=resource.person_id,
                    department=sponsor.department if sponsor else None,
                    risk_tier=details.get("risk_tier"),
                    status=resource.status,
                    orphan=bool(reasons),
                    orphan_reasons=reasons,
                )
            )
            edges.append(
                WorkforceEdge(
                    source=str(resource.person_id),
                    target=resource.resource_key,
                    kind="SPONSOR",
                )
            )
        elif (
            resource.resource_type not in AGENT_RESOURCE_TYPES
            and resource.status not in TERMINAL_RESOURCE_STATES
        ):
            access_counts[resource.person_id] = (
                access_counts.get(resource.person_id, 0) + 1
            )

    nodes = [
        PersonNode(
            id=person.id,
            name=person.name,
            department=person.department,
            job_title=person.job_title,
            app_role=person.app_role,
            employment_status=person.employment_status,
            access_count=access_counts.get(person.id, 0),
        )
        for person in people
    ]
    for person in people:
        if person.manager_id is not None and person.manager_id in people_by_id:
            edges.append(
                WorkforceEdge(
                    source=str(person.manager_id),
                    target=str(person.id),
                    kind="MANAGER",
                )
            )

    nodes.sort(key=lambda node: (node.department or "", node.name))
    agents.sort(key=lambda node: node.resource_key)
    edges.sort(key=lambda edge: (edge.kind, edge.source, edge.target))
    return WorkforceGraph(people=nodes, agents=agents, edges=edges)


def _agent_resources(db: Session) -> list[CompanyResource]:
    return list(
        db.scalars(
            select(CompanyResource)
            .where(CompanyResource.resource_type == ResourceType.AI_AGENT)
            .order_by(CompanyResource.resource_key)
        )
    )


def list_agents(db: Session, *, now: datetime | None = None) -> list[AgentSummary]:
    now = now or _now()
    return [
        build_agent_summary(agent, db.get(Person, agent.person_id), now)
        for agent in _agent_resources(db)
    ]


def list_orphan_agents(db: Session, *, now: datetime | None = None) -> list[AgentSummary]:
    return [agent for agent in list_agents(db, now=now) if agent.orphan]


def _get_agent_resource(db: Session, resource_key: str) -> CompanyResource:
    agent = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == resource_key,
            CompanyResource.resource_type == ResourceType.AI_AGENT,
        )
    )
    if agent is None:
        raise AgentNotFoundError(f"Agent does not exist: {resource_key}")
    return agent


def get_agent(db: Session, resource_key: str) -> AgentSummary:
    agent = _get_agent_resource(db, resource_key)
    return build_agent_summary(agent, db.get(Person, agent.person_id), _now())


def get_agent_grants(db: Session, resource_key: str) -> list[AgentCredential]:
    """Credentials held by the agent. Temporary MCP grants join this in W5."""
    agent = _get_agent_resource(db, resource_key)
    credential_key = (agent.details_data or {}).get("credential_key")
    credentials = db.scalars(
        select(CompanyResource)
        .where(CompanyResource.resource_type == ResourceType.AGENT_CREDENTIAL)
        .order_by(CompanyResource.resource_key)
    )
    return [
        build_credential(credential)
        for credential in credentials
        if credential.resource_key == credential_key
        or (credential.details_data or {}).get("agent_key") == resource_key
    ]


def get_workforce_graph(db: Session) -> WorkforceGraph:
    people = db.scalars(select(Person))
    resources = db.scalars(select(CompanyResource))
    return build_workforce_graph(people, resources, _now())
