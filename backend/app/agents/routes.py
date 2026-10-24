from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.schemas import AgentCredential, AgentSummary, WorkforceGraph
from app.agents.service import (
    AgentNotFoundError,
    get_agent,
    get_agent_grants,
    get_workforce_graph,
    list_agents,
    list_orphan_agents,
)
from app.database import get_db


router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentSummary])
def read_agents(db: Session = Depends(get_db)) -> list[AgentSummary]:
    return list_agents(db)


# Declared before /agents/{resource_key} so "orphans" is not read as a key.
@router.get("/agents/orphans", response_model=list[AgentSummary])
def read_orphan_agents(db: Session = Depends(get_db)) -> list[AgentSummary]:
    return list_orphan_agents(db)


@router.get("/agents/{resource_key}", response_model=AgentSummary)
def read_agent(resource_key: str, db: Session = Depends(get_db)) -> AgentSummary:
    try:
        return get_agent(db, resource_key)
    except AgentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/agents/{resource_key}/grants", response_model=list[AgentCredential])
def read_agent_grants(
    resource_key: str,
    db: Session = Depends(get_db),
) -> list[AgentCredential]:
    try:
        return get_agent_grants(db, resource_key)
    except AgentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/workforce/graph", response_model=WorkforceGraph)
def read_workforce_graph(db: Session = Depends(get_db)) -> WorkforceGraph:
    return get_workforce_graph(db)
