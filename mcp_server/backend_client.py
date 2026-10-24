"""HTTP calls from the MCP adapter to the LivingOps backend.

The adapter holds no state and makes no decisions: it forwards the calling
agent's key and returns the backend's answer. Errors come back as plain data
so an agent can read why a request failed.
"""
from __future__ import annotations

from typing import Any

import httpx


AGENT_KEY_HEADER = "X-Agent-Key"


class BackendClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    async def call(
        self,
        method: str,
        path: str,
        agent_key: str | None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        if not agent_key:
            return {"error": 401, "detail": f"Send your agent key in the {AGENT_KEY_HEADER} header."}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            try:
                response = await client.request(
                    method, path, json=json, headers={AGENT_KEY_HEADER: agent_key}
                )
            except httpx.HTTPError as error:
                return {"error": 503, "detail": f"LivingOps backend unreachable: {error}"}
        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text[:500]}
        if response.is_error:
            detail = body.get("detail") if isinstance(body, dict) else body
            return {"error": response.status_code, "detail": detail}
        return body
