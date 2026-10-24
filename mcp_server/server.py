"""LivingOps MCP Access Gateway (Streamable HTTP).

A thin adapter in front of the synchronous backend: every tool forwards the
agent's `X-Agent-Key` header to the backend REST API, which authenticates the
agent by key hash, applies the deterministic risk tier, runs approvals and
execution, and audits everything. Nothing is decided or stored here.

Run: python -m mcp_server            (from the project root)
Env: LIVINGOPS_BACKEND_URL (default http://127.0.0.1:8000),
     MCP_HOST (127.0.0.1), MCP_PORT (8765)
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from mcp_server.backend_client import AGENT_KEY_HEADER, BackendClient


backend = BackendClient(os.environ.get("LIVINGOPS_BACKEND_URL", "http://127.0.0.1:8000"))

server = MCPServer(
    name="livingops-access-gateway",
    instructions=(
        "Request time-limited access to company systems for this AI agent. "
        "Low-risk read access is approved automatically; write access or "
        "confidential repositories wait for the IT Owner; production and admin "
        "access is always denied. Every grant expires."
    ),
)


def _agent_key(ctx: Context) -> str | None:
    headers = ctx.headers or {}
    return headers.get(AGENT_KEY_HEADER.lower()) or headers.get(AGENT_KEY_HEADER)


@server.tool()
async def whoami(ctx: Context) -> Any:
    """Who am I: agent name, human sponsor, scopes, and whether I am orphaned."""
    return await backend.call("GET", "/agent-identity", _agent_key(ctx))


@server.tool()
async def request_access(
    resource: str,
    permission: str,
    duration_minutes: int,
    reason: str,
    ctx: Context,
    system: str = "github",
) -> Any:
    """Ask for temporary access, e.g. resource="aurora", permission="write",
    duration_minutes=120. Returns the request id, risk tier and state."""
    return await backend.call(
        "POST",
        "/access-requests",
        _agent_key(ctx),
        json={
            "system": system,
            "resource": resource,
            "permission": permission,
            "duration_minutes": duration_minutes,
            "reason": reason,
        },
    )


@server.tool()
async def check_request(request_id: str, ctx: Context) -> Any:
    """State of a request: PENDING_APPROVAL, ACTIVE, DENIED, REJECTED,
    RELEASED or EXPIRED, with the expiry time once active."""
    return await backend.call("GET", f"/access-requests/{request_id}", _agent_key(ctx))


@server.tool()
async def list_my_access(ctx: Context) -> Any:
    """All my credentials and temporary grants with their expiry."""
    return await backend.call("GET", "/access-grants/mine", _agent_key(ctx))


@server.tool()
async def release_access(grant_key: str, ctx: Context) -> Any:
    """Give a temporary grant back as soon as the work is done."""
    return await backend.call(
        "POST", f"/access-grants/{grant_key}/release", _agent_key(ctx)
    )


def main() -> None:
    import anyio

    anyio.run(
        lambda: server.run_streamable_http_async(
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8765")),
        )
    )


if __name__ == "__main__":
    main()
