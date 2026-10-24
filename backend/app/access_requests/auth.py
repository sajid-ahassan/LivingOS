"""Agent identity for the MCP gateway.

Each agent has its own API key. The MCP adapter forwards it in the
`X-Agent-Key` header; the backend stores only a SHA-256 hash on the agent's
AI_AGENT resource and looks the agent up by that hash.
"""
from __future__ import annotations

import hashlib
import hmac

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ResourceType
from app.models import CompanyResource


class AgentAuthError(PermissionError):
    pass


def hash_agent_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def authenticate_agent(db: Session, raw_key: str | None) -> CompanyResource:
    if not raw_key:
        raise AgentAuthError("Missing X-Agent-Key header.")
    key_hash = hash_agent_key(raw_key)
    agent = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_type == ResourceType.AI_AGENT,
            CompanyResource.details_data["mcp_api_key_hash"].astext == key_hash,
        )
    )
    stored = ((agent.details_data or {}).get("mcp_api_key_hash") if agent else "") or ""
    if agent is None or not hmac.compare_digest(stored, key_hash):
        raise AgentAuthError("Unknown agent key.")
    return agent


def check_service_token(provided: str | None, expected: str) -> None:
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        raise AgentAuthError("Invalid service token.")
