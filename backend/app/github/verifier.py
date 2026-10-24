"""Independent verification against GitHub.

After n8n reports success, the backend asks GitHub itself, with its own
read-only token, whether the change really happened. n8n's response is never
used as evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.enums import ActionType
from app.github.client import GitHubReadClient, GitHubReadError


@dataclass
class GitHubVerification:
    ok: bool
    problems: list[str] = field(default_factory=list)
    observed: dict[str, Any] = field(default_factory=dict)
    new_key_id: int | None = None


def _verify_collaborator(
    action_type: ActionType,
    params: dict[str, Any],
    client: GitHubReadClient,
) -> GitHubVerification:
    owner, repo, username = params["owner"], params["repo"], params["username"]
    if action_type == ActionType.REVOKE:
        present = client.is_collaborator(owner, repo, username)
        observed = {"collaborator": present}
        if present:
            return GitHubVerification(False, [f"{username} is still a collaborator"], observed)
        return GitHubVerification(True, observed=observed)

    permission = client.collaborator_permission(owner, repo, username)
    observed = {"permission": permission}
    if permission != "read":
        return GitHubVerification(
            False, [f"{username} has {permission} access, expected read"], observed
        )
    return GitHubVerification(True, observed=observed)


def _verify_deploy_key(
    action_type: ActionType,
    params: dict[str, Any],
    client: GitHubReadClient,
) -> GitHubVerification:
    keys = client.list_deploy_keys(params["owner"], params["repo"])
    by_id = {int(key["id"]): key for key in keys}
    old_key_id = params.get("key_id")
    problems: list[str] = []
    observed: dict[str, Any] = {"key_ids": sorted(by_id)}

    if old_key_id is not None and int(old_key_id) in by_id:
        problems.append(f"old deploy key {old_key_id} still exists")

    if action_type == ActionType.REVOKE:
        return GitHubVerification(not problems, problems, observed)

    matches = [key for key in keys if key.get("title") == params["key_title"]]
    if len(matches) != 1:
        problems.append(
            f"expected one deploy key titled {params['key_title']}, found {len(matches)}"
        )
        return GitHubVerification(False, problems, observed)

    new_key = matches[0]
    observed["new_key"] = {
        "id": new_key["id"],
        "read_only": new_key.get("read_only"),
    }
    if bool(new_key.get("read_only")) != bool(params["read_only"]):
        expected = "read-only" if params["read_only"] else "write"
        problems.append(f"new deploy key is not {expected}")
    return GitHubVerification(
        not problems, problems, observed, new_key_id=int(new_key["id"])
    )


def verify_github_action(
    action_type: ActionType,
    params: dict[str, Any],
    client: GitHubReadClient,
) -> GitHubVerification:
    try:
        if params.get("kind") == "collaborator":
            return _verify_collaborator(action_type, params, client)
        if params.get("kind") == "deploy_key":
            return _verify_deploy_key(action_type, params, client)
    except GitHubReadError as error:
        return GitHubVerification(False, [f"GitHub check failed: {error}"])
    return GitHubVerification(False, [f"unknown GitHub target kind: {params.get('kind')}"])
