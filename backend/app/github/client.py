"""Read-only GitHub REST client used for independent verification.

It only issues GET requests with the backend's read-only token. All writes
go through the n8n executor, which holds the write token.
"""
from __future__ import annotations

from typing import Any

import requests

from app.config import get_settings


class GitHubReadError(RuntimeError):
    pass


class GitHubReadClient:
    def __init__(
        self,
        *,
        token: str,
        api_url: str = "https://api.github.com",
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str) -> requests.Response:
        try:
            return self._session.get(
                f"{self._api_url}{path}",
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            raise GitHubReadError(f"GitHub is unreachable: {error}") from error

    def is_collaborator(self, owner: str, repo: str, username: str) -> bool:
        response = self._get(f"/repos/{owner}/{repo}/collaborators/{username}")
        if response.status_code == 204:
            return True
        if response.status_code == 404:
            return False
        raise GitHubReadError(
            f"Collaborator check returned HTTP {response.status_code}."
        )

    def collaborator_permission(self, owner: str, repo: str, username: str) -> str:
        response = self._get(
            f"/repos/{owner}/{repo}/collaborators/{username}/permission"
        )
        if response.status_code == 404:
            return "none"
        if not response.ok:
            raise GitHubReadError(
                f"Permission check returned HTTP {response.status_code}."
            )
        return str(response.json().get("permission", "none"))

    def list_deploy_keys(self, owner: str, repo: str) -> list[dict[str, Any]]:
        response = self._get(f"/repos/{owner}/{repo}/keys?per_page=100")
        if not response.ok:
            raise GitHubReadError(
                f"Deploy key listing returned HTTP {response.status_code}."
            )
        keys = response.json()
        if not isinstance(keys, list):
            raise GitHubReadError("Deploy key listing was not a list.")
        return keys


def get_read_client() -> GitHubReadClient:
    settings = get_settings()
    return GitHubReadClient(
        token=settings.github_read_token,
        api_url=settings.github_api_url,
        timeout=settings.request_timeout_seconds,
    )
