"""Put the GitHub demo org back to the start of the story.

A rehearsal removes Arif from `aurora` and rotates or deletes the bot's
deploy keys. Before the database is reset, this module plans the GitHub
calls that undo that, sends them through the n8n executor (the backend only
holds the read-only token), then checks the result with that read-only token
and saves the new bot key id for seed_company.

Only keys LivingOps created (title `livingops:...`) are touched.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import Settings, get_settings
from app.execution.n8n_client import dispatch_to_n8n
from app.github.client import GitHubReadClient, get_read_client
from app.github.keys import generate_public_key
from app.scripts.link_github_demo import BOT_KEY_TITLE, load_demo_ids, save_demo_ids


KEY_PREFIX = "livingops:"
WRITE_PERMISSIONS = {"write", "maintain", "admin"}


def _payload(action_type: str, resource_key: str, step: str, github: dict[str, Any]) -> dict[str, Any]:
    # Same shape as an executor payload; n8n reads target, action_type and
    # requested_data.github. These calls belong to no case.
    return {
        "action_id": f"reset-demo:{step}",
        "case_id": None,
        "person_id": None,
        "action_type": action_type,
        "resource_type": "GITHUB",
        "resource_key": resource_key,
        "idempotency_key": f"reset-demo:{step}",
        "target": "github",
        "requested_data": {"github": github},
    }


def _bot_write_key(keys: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [k for k in keys if k.get("title") == BOT_KEY_TITLE and not k.get("read_only")]
    return matches[0] if len(matches) == 1 else None


def plan_restore(
    keys: list[dict[str, Any]],
    arif_permission: str | None,
    *,
    settings: Settings,
    new_public_key: Callable[[str], str],
) -> list[dict[str, Any]]:
    """Executor payloads, in order: delete stray keys, add the bot's write
    key if it is missing, give Arif write access back."""
    base = {"owner": settings.github_org, "repo": settings.github_repo}
    keep = _bot_write_key(keys)
    payloads = []

    for key in keys:
        if key is keep or not str(key.get("title", "")).startswith(KEY_PREFIX):
            continue
        payloads.append(_payload(
            "REVOKE", "credential:aurora-release-bot", f"delete-key-{key['id']}",
            {**base, "kind": "deploy_key", "key_id": int(key["id"])},
        ))

    if keep is None:
        payloads.append(_payload(
            "REASSIGN", "credential:aurora-release-bot", "add-bot-key",
            {
                **base,
                "kind": "deploy_key",
                "key_title": BOT_KEY_TITLE,
                "public_key": new_public_key(BOT_KEY_TITLE),
                "read_only": False,
            },
        ))

    if arif_permission is not None and arif_permission not in WRITE_PERMISSIONS:
        # The executor turns a collaborator DOWNSCOPE into
        # PUT /collaborators/{username} with the given permission.
        payloads.append(_payload(
            "DOWNSCOPE", "github:aurora:arif", "arif-write",
            {**base, "kind": "collaborator", "username": settings.github_arif_username,
             "permission": "push"},
        ))
    return payloads


def restore_github_demo(
    *,
    settings: Settings | None = None,
    client: GitHubReadClient | None = None,
    dispatch: Callable[[dict[str, Any]], dict[str, Any]] = dispatch_to_n8n,
    new_public_key: Callable[[str], str] = generate_public_key,
) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.github_enabled:
        return {"skipped": "GitHub is not configured"}
    if settings.demo_mode.upper() == "OFFLINE":
        return {"skipped": "OFFLINE mode"}

    client = client or get_read_client()
    owner, repo = settings.github_org, settings.github_repo
    username = settings.github_arif_username or None

    keys = client.list_deploy_keys(owner, repo)
    arif_before = client.collaborator_permission(owner, repo, username) if username else None
    payloads = plan_restore(
        keys, arif_before, settings=settings, new_public_key=new_public_key
    )
    for payload in payloads:
        dispatch(payload)

    # Check GitHub itself, never n8n's answer.
    keys_after = client.list_deploy_keys(owner, repo)
    bot_key = _bot_write_key(keys_after)
    if bot_key is None:
        raise RuntimeError(f"No single write deploy key titled {BOT_KEY_TITLE!r} after the restore.")
    stray = [k["id"] for k in keys_after if str(k.get("title", "")).startswith(KEY_PREFIX) and k is not bot_key]
    if stray:
        raise RuntimeError(f"LivingOps deploy keys still on {repo}: {stray}")

    save_demo_ids({**load_demo_ids(), "aurora_release_bot_key_id": int(bot_key["id"])})

    report: dict[str, Any] = {
        "github_calls": len(payloads),
        "bot_key_id": int(bot_key["id"]),
    }
    if username:
        arif_after = client.collaborator_permission(owner, repo, username)
        # An outside collaborator who was removed gets an invitation instead
        # of access; it must be accepted with Arif's test account.
        report["arif_access"] = (
            arif_after if arif_after in WRITE_PERMISSIONS else "invitation pending"
        )
    return report
