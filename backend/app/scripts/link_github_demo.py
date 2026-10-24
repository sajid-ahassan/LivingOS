"""Link the real GitHub demo organization to the seeded story resources.

Finds Aurora Release Bot's deploy key on the `aurora` repository with the
backend's read-only token, saves its id to data/seed/demo_ids.json (git-
ignored, environment-specific) and records it on the bot's credential, so
DOWNSCOPE and REVOKE of that credential run against real GitHub.

Run after adding the key (title livingops:aurora-release-bot, write access):
    python -m app.scripts.link_github_demo
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.config import PROJECT_ROOT, get_settings
from app.database import SessionLocal
from app.github.client import get_read_client
from app.models import CompanyResource


DEMO_IDS_PATH = PROJECT_ROOT / "data" / "seed" / "demo_ids.json"
BOT_KEY_TITLE = "livingops:aurora-release-bot"
BOT_CREDENTIAL_KEY = "credential:aurora-release-bot"


def load_demo_ids() -> dict[str, Any]:
    if not DEMO_IDS_PATH.exists():
        return {}
    try:
        return json.loads(DEMO_IDS_PATH.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def save_demo_ids(values: dict[str, Any]) -> None:
    DEMO_IDS_PATH.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")


def find_bot_key(keys: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [key for key in keys if key.get("title") == BOT_KEY_TITLE]
    return matches[0] if len(matches) == 1 else None


def apply_bot_key(details: dict[str, Any], key_id: int) -> dict[str, Any]:
    github = {**(details.get("github") or {}), "repo": get_settings().github_repo, "key_id": key_id}
    return {**details, "github": github, "permission": "write"}


def main() -> None:
    settings = get_settings()
    if not settings.github_enabled:
        raise SystemExit("Set GITHUB_ORG and GITHUB_READ_TOKEN in .env first.")

    keys = get_read_client().list_deploy_keys(settings.github_org, settings.github_repo)
    key = find_bot_key(keys)
    if key is None:
        raise SystemExit(
            f"Found {len(keys)} deploy key(s) but not exactly one titled {BOT_KEY_TITLE!r}."
        )
    if key.get("read_only"):
        raise SystemExit("The bot's deploy key is read-only; the story starts with write access.")

    ids = {**load_demo_ids(), "aurora_release_bot_key_id": int(key["id"])}
    save_demo_ids(ids)

    with SessionLocal() as db:
        credential = db.scalar(
            select(CompanyResource).where(CompanyResource.resource_key == BOT_CREDENTIAL_KEY)
        )
        if credential is None:
            raise SystemExit("Seed the company first (python -m app.scripts.seed_company).")
        credential.details_data = apply_bot_key(credential.details_data or {}, int(key["id"]))
        db.commit()

    print(f"Linked {BOT_CREDENTIAL_KEY} to deploy key {key['id']} (write) on "
          f"{settings.github_org}/{settings.github_repo}; saved to {DEMO_IDS_PATH.name}.")


if __name__ == "__main__":
    main()
