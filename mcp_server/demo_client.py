"""Scripted MCP client that plays Aurora Release Bot in demo scene 5.

It connects to the gateway like any standard MCP agent, asks who it is, then
asks for two hours of write access to the confidential `aurora` repository
(HIGH tier: the IT Owner must approve) and waits until access is ACTIVE or
refused. With --low it first makes a read request on a normal repository,
which the rules approve automatically.

Run (project root, gateway and backend running):
    python -m mcp_server.demo_client [--low] [--release]
The agent key is read from AURORA_BOT_MCP_KEY in the environment or .env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from mcp_server.backend_client import AGENT_KEY_HEADER


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_STATES = {"ACTIVE", "DENIED", "REJECTED", "FAILED", "EXPIRED", "RELEASED"}


def _agent_key() -> str:
    try:
        from dotenv import dotenv_values

        file_values = dotenv_values(PROJECT_ROOT / ".env")
    except ImportError:
        file_values = {}
    key = os.environ.get("AURORA_BOT_MCP_KEY") or file_values.get("AURORA_BOT_MCP_KEY")
    if not key:
        raise SystemExit("Set AURORA_BOT_MCP_KEY (the bot's key) in .env first.")
    return key


def _result(call_result: Any) -> Any:
    structured = getattr(call_result, "structured_content", None) or getattr(
        call_result, "structuredContent", None
    )
    if structured is not None:
        return structured.get("result", structured) if isinstance(structured, dict) else structured
    # A list comes back as one text block per item.
    values = []
    for block in getattr(call_result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                values.append(json.loads(text))
            except ValueError:
                values.append(text)
    if not values:
        return None
    return values[0] if len(values) == 1 else values


def _say(title: str, data: Any) -> None:
    print(f"\n=== {title}")
    print(json.dumps(data, indent=2, default=str))


async def _wait_for_decision(session: ClientSession, request_id: str, seconds: int) -> Any:
    status: Any = None
    for _ in range(max(1, seconds // 3)):
        status = _result(await session.call_tool("check_request", {"request_id": request_id}))
        state = status.get("state") if isinstance(status, dict) else None
        print(f"  ... {state}")
        if state in FINAL_STATES:
            break
        await asyncio.sleep(3)
    return status


async def run(url: str, low: bool, release: bool, wait_seconds: int) -> None:
    http_client = create_mcp_http_client(headers={AGENT_KEY_HEADER: _agent_key()})
    async with streamable_http_client(url, http_client=http_client) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            _say("whoami", _result(await session.call_tool("whoami", {})))

            if low:
                low_request = _result(await session.call_tool("request_access", {
                    "resource": "helios",
                    "permission": "read",
                    "duration_minutes": 60,
                    "reason": "Read Helios release notes to cross-link the Aurora changelog.",
                }))
                _say("LOW-risk read request (rules approve it at once)", low_request)

            high = _result(await session.call_tool("request_access", {
                "resource": "aurora",
                "permission": "write",
                "duration_minutes": 120,
                "reason": "Tag Aurora release v2.4 and publish its changelog.",
            }))
            _say("HIGH-risk write request (waits for the IT Owner)", high)

            if isinstance(high, dict) and high.get("request_id"):
                final = await _wait_for_decision(session, str(high["request_id"]), wait_seconds)
                _say("Decision", final)

            grants = _result(await session.call_tool("list_my_access", {}))
            _say("list_my_access", grants)

            if release and isinstance(grants, list):
                for grant in grants:
                    if grant.get("temporary") and grant.get("status") == "ACTIVE":
                        released = _result(await session.call_tool(
                            "release_access", {"grant_key": grant["resource_key"]}
                        ))
                        _say(f"release_access {grant['resource_key']}", released)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurora Release Bot MCP demo client.")
    parser.add_argument("--url", default=os.environ.get("MCP_URL", "http://127.0.0.1:8765/mcp"))
    parser.add_argument("--low", action="store_true", help="also make a LOW-risk read request")
    parser.add_argument("--release", action="store_true", help="release active grants at the end")
    parser.add_argument("--wait", type=int, default=180, help="seconds to wait for approval")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.low, args.release, args.wait))


if __name__ == "__main__":
    main()
