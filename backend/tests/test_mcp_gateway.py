from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("mcp")

from mcp.client.client import Client  # noqa: E402

from mcp_server.backend_client import AGENT_KEY_HEADER, BackendClient  # noqa: E402
from mcp_server.demo_client import _result  # noqa: E402
from mcp_server.server import server  # noqa: E402


def _client(handler) -> BackendClient:
    return BackendClient("http://backend", transport=httpx.MockTransport(handler))


def test_gateway_forwards_agent_key_and_body():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get(AGENT_KEY_HEADER)
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"state": "PENDING_APPROVAL", "tier": "HIGH"})

    result = asyncio.run(_client(handler).call(
        "POST", "/access-requests", "bot-key", json={"resource": "aurora"}
    ))
    assert result == {"state": "PENDING_APPROVAL", "tier": "HIGH"}
    assert seen == {"key": "bot-key", "path": "/access-requests", "body": {"resource": "aurora"}}


def test_backend_errors_come_back_as_readable_data():
    async def handler(request):
        return httpx.Response(401, json={"detail": "Unknown agent key."})

    result = asyncio.run(_client(handler).call("GET", "/agent-identity", "wrong"))
    assert result == {"error": 401, "detail": "Unknown agent key."}


def test_missing_key_never_reaches_the_backend():
    async def handler(request):
        raise AssertionError("backend must not be called without a key")

    result = asyncio.run(_client(handler).call("GET", "/agent-identity", None))
    assert result["error"] == 401


def test_unreachable_backend_is_reported():
    async def handler(request):
        raise httpx.ConnectError("refused")

    result = asyncio.run(_client(handler).call("GET", "/agent-identity", "k"))
    assert result["error"] == 503


def test_gateway_exposes_the_five_planned_tools():
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"whoami", "request_access", "check_request", "list_my_access", "release_access"}


def test_standard_mcp_client_can_call_a_tool_in_memory():
    async def scenario():
        async with Client(server) as client:
            # In-memory transport carries no headers, so the adapter refuses
            # before touching the backend.
            return await client.call_tool("whoami", {})

    result = _result(asyncio.run(scenario()))
    assert result["error"] == 401
