"""Rehearse demo scenes 5-6 through the real API, after rehearse_hero.

Scene 5: Aurora Release Bot asks for access the way its MCP gateway would
(X-Agent-Key): a read on helios (LOW, approved by the rules) and two hours of
write on the confidential aurora repository (HIGH, Tahmid approves). The grant
is left active, as on stage.
Scene 6: Tahmid activates Access Policy V2. The Guardian must flag the live
write grant (rule 7: the sponsor lacks confidential-repo training) and the
lesson from scene 3; the grant is remediated to read-only and approved.

The MCP gateway is a thin adapter over these same endpoints; test it on its
own with mcp_server.demo_client. Run after rehearse_hero; reset_demo after.

Run: python -m app.scripts.rehearse_access_policy [--executor offline|n8n]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from app.config import get_settings
from app.scripts.rehearse_hero import RehearsalError, TAHMID


def _call(client: TestClient, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> Any:
    response = client.request(method, path, json=body, headers=headers or {})
    if response.status_code >= 400:
        raise RehearsalError(f"{method} {path} -> HTTP {response.status_code}: {response.text[:800]}")
    return response.json()


def rehearse(executor: str) -> dict[str, Any]:
    from app.main import app

    if executor == "offline":
        from app.demo.offline_executor import dispatch_offline
        from app.execution import service as execution_service

        execution_service.dispatch_to_n8n = dispatch_offline

    key = get_settings().aurora_bot_mcp_key
    if not key:
        raise RehearsalError("Set AURORA_BOT_MCP_KEY in .env.")
    bot = {"X-Agent-Key": key}
    client = TestClient(app)
    timings: dict[str, float] = {}
    summary: dict[str, Any] = {"executor": executor}

    # Scene 5: the bot asks for access.
    t0 = time.perf_counter()
    low = _call(client, "POST", "/access-requests", {
        "system": "github", "resource": "helios", "permission": "read", "duration_minutes": 60,
        "reason": "Read Helios release notes to cross-link the Aurora changelog.",
    }, bot)
    high = _call(client, "POST", "/access-requests", {
        "system": "github", "resource": "aurora", "permission": "write", "duration_minutes": 120,
        "reason": "Tag Aurora release v2.4 and publish its changelog.",
    }, bot)
    summary["low"] = {k: low.get(k) for k in ("state", "tier")}
    summary["high_before"] = {k: high.get(k) for k in ("state", "tier", "tier_reasons")}
    approval = next(
        a for a in _call(client, "GET", f"/approvals?assigned_to={TAHMID}")
        if a.get("origin") == "MCP_ACCESS_REQUEST" and str(a.get("case_id")) == str(high["request_id"])
    )
    summary["approver_note"] = (approval.get("approver_note") or "")[:300]
    _call(client, "POST", f"/approvals/{approval['id']}/decision", {
        "decided_by": TAHMID, "decision": "APPROVED", "comment": "Approved for the v2.4 release.",
    })
    status = _call(client, "GET", f"/access-requests/{high['request_id']}", headers=bot)
    summary["high_after"] = {k: status.get(k) for k in ("state", "expires_at")}
    if status.get("state") != "ACTIVE":
        raise RehearsalError(f"HIGH grant is {status.get('state')}, expected ACTIVE")
    timings["scene5_access_s"] = round(time.perf_counter() - t0, 1)

    # Scene 6: a new policy version re-checks everything that relied on V1.
    t0 = time.perf_counter()
    draft = _call(client, "GET", "/demo/policies/access/v2")
    result = _call(client, "POST", "/policy-guardian/activate", {
        "policy_code": "ACCESS", "title": "Access Policy", "version_number": draft["version"],
        "department": "GLOBAL", "effective_from": date.today().isoformat(),
        "uploaded_by": TAHMID, "content_text": draft["content_text"],
    })
    timings["scene6_guardian_s"] = round(time.perf_counter() - t0, 1)
    change_id = result["policy_change"]["id"]
    view = _call(client, "GET", f"/policy-guardian/changes/{change_id}/view")
    actionable = [i for i in view["impacts"] if i["recommended_action"] != "NO_ACTION"]
    summary["impacts"] = [
        f"{i['target_type']} {i['risk_level']} {i['recommended_action']} {(i.get('target') or {}).get('resource_key') or (i.get('target') or {}).get('label') or ''}"
        for i in actionable
    ]
    summary["history_only_impacts"] = len(view["impacts"]) - len(actionable)
    if not any(i["target_type"] == "LEARNING" for i in actionable):
        raise RehearsalError("Guardian did not flag the scene-3 lesson.")
    grant_impact = next(
        (i for i in actionable if i["target_type"] == "RESOURCE" and i["recommended_action"] == "REGENERATE"
         and ":grant:" in str((i.get("target") or {}).get("resource_key"))),
        None,
    )
    if grant_impact is None:
        raise RehearsalError("Guardian did not flag the live write grant.")

    t0 = time.perf_counter()
    remediation = _call(client, "POST", f"/policy-guardian/impacts/{grant_impact['id']}/remediate", {"requested_by": TAHMID})
    _call(client, "POST", f"/approvals/{remediation['approval_id']}/decision", {
        "decided_by": str(remediation["assigned_to"]), "decision": "APPROVED", "comment": "Downscope under Access Policy V2.",
    })
    grants = _call(client, "GET", "/access-grants/mine", headers=bot)
    grant_key = grant_impact["target"]["resource_key"]
    summary["grant_after"] = next(
        ({k: g.get(k) for k in ("resource_key", "status", "permission")} for g in grants if g.get("resource_key") == grant_key), None
    )
    timings["scene6_remediation_s"] = round(time.perf_counter() - t0, 1)
    summary["policy_change_id"] = change_id
    summary["timings"] = timings
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Rehearse demo scenes 5-6.")
    parser.add_argument("--executor", choices=["offline", "n8n"], default="offline")
    args = parser.parse_args()
    print(json.dumps(rehearse(args.executor), indent=2, default=str))


if __name__ == "__main__":
    main()
