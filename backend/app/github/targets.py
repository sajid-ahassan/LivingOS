"""Decide whether an action runs against the real GitHub demo org.

A resource is GitHub-backed when its details carry a `github` block naming
the repository and either a collaborator (`username`, or `demo_account`
mapped to a configured test account) or an existing deploy key (`key_id`).
Without GitHub configuration, or in OFFLINE demo mode, everything falls back
to the mock company path, so the demo keeps working.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import Settings
from app.enums import ActionType, ResourceType
from app.github.keys import key_title
from app.models import CompanyResource


GITHUB_ACTIONS = {
    ResourceType.GITHUB_ACCESS: {ActionType.REVOKE, ActionType.DOWNSCOPE},
    # Agent Policy rule 6: a credential is rotated whenever its sponsor or
    # scope changes, so REASSIGN and DOWNSCOPE both issue a new deploy key.
    ResourceType.AGENT_CREDENTIAL: {
        ActionType.REVOKE,
        ActionType.REASSIGN,
        ActionType.DOWNSCOPE,
    },
}


def _username(github: dict[str, Any], settings: Settings) -> str | None:
    if github.get("username"):
        return str(github["username"])
    if github.get("demo_account") == "ARIF" and settings.github_arif_username:
        return settings.github_arif_username
    return None


def build_github_parameters(
    action_type: ActionType,
    resource: CompanyResource,
    *,
    settings: Settings,
    idempotency_key: str,
    new_public_key: Callable[[str], str],
) -> dict[str, Any] | None:
    """Parameters n8n needs for a real GitHub call, or None for the mock path."""
    if not settings.github_enabled or settings.demo_mode.upper() == "OFFLINE":
        return None
    if action_type not in GITHUB_ACTIONS.get(resource.resource_type, set()):
        return None

    details = resource.details_data or {}
    github = details.get("github") or {}
    repo = github.get("repo")
    if not repo:
        return None
    base = {"owner": settings.github_org, "repo": repo}

    if resource.resource_type == ResourceType.GITHUB_ACCESS:
        username = _username(github, settings)
        if not username:
            return None
        parameters = {**base, "kind": "collaborator", "username": username}
        if action_type == ActionType.DOWNSCOPE:
            parameters["permission"] = "pull"
        return parameters

    key_id = github.get("key_id")
    if not key_id:
        return None
    parameters = {**base, "kind": "deploy_key", "key_id": int(key_id)}
    if action_type == ActionType.REVOKE:
        return parameters

    title = key_title(resource.resource_key, idempotency_key)
    read_only = (
        True
        if action_type == ActionType.DOWNSCOPE
        else details.get("permission") == "read"
    )
    return {
        **parameters,
        "key_title": title,
        "public_key": new_public_key(title),
        "read_only": read_only,
    }
