"""Rehearse the hero story (demo scenes 2-4) through the real API.

Arif Hossain leaves; the AI drafts his offboarding plan, including his two
agents; manager Nabil revises it (keep Aurora Release Bot, read-only, under
himself); the revision is approved and executed; every action is verified;
the correction becomes an approved, indexed lesson.

Runs in-process with FastAPI's TestClient against the configured database,
so it exercises the same code as the UI. Run it after `reset_demo`; run
`reset_demo` again afterwards. In LIVE mode the AI answers are recorded to
data/demo_cache/, so a second run in CACHED_AI mode must produce the same plan.

Run: python -m app.scripts.rehearse_hero [--executor offline|n8n]
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any

from fastapi.testclient import TestClient


FARHANA = "11111111-1111-4111-8111-111111111111"
NABIL = "22222222-2222-4222-8222-222222222222"
TAHMID = "33333333-3333-4333-8333-333333333333"
ARIF = "66666666-6666-4666-8666-666666666666"

RELEASE_BOT = "agent:aurora-release-bot"
RELEASE_BOT_CREDENTIAL = "credential:aurora-release-bot"

CASE_FACTS = {
    "last_working_day": "2026-12-26",
    "manager_id": NABIL,
    "successor_person_id": NABIL,
    "department": "ENGINEERING",
    "job_title": "Senior Software Engineer",
}

# The correction must describe what actually changed, because the learning
# step turns it into a lesson; it depends on what the AI proposed.
CORRECTIONS = {
    "REVOKE": (
        "Do not shut down Aurora Release Bot: Aurora is still shipping. Hand the "
        "bot to me (Nabil) and downscope its deploy key from write to read-only."
    ),
    "REASSIGN": (
        "Keep Aurora Release Bot with me (Nabil) as proposed, but downscope its "
        "deploy key from write to read-only: it should not keep write access to "
        "the confidential Aurora repository after its sponsor leaves."
    ),
}


class RehearsalError(RuntimeError):
    pass


def _call(client: TestClient, method: str, path: str, body: dict | None = None) -> Any:
    response = client.request(method, path, json=body)
    if response.status_code >= 400:
        raise RehearsalError(f"{method} {path} -> HTTP {response.status_code}: {response.text[:800]}")
    return response.json()


def _flatten(plan_data: dict) -> list[dict]:
    actions = [
        *plan_data.get("revocations", []),
        *plan_data.get("asset_returns", []),
        *plan_data.get("reassignments", []),
    ]
    return sorted(actions, key=lambda action: action["sequence"])


def _evidence_by_code(context: dict) -> dict[str, str]:
    return {item["policy_code"]: item["evidence_id"] for item in context["evidence"]}


def _nabil_revision(ai_actions: list[dict], evidence: dict[str, str]) -> list[dict]:
    agent_evidence = [evidence["ACCESS"], evidence["AGENT"]]
    revised = []
    for action in ai_actions:
        action = dict(action)
        if action["resource_key"] == RELEASE_BOT:
            action.update(
                action_type="REASSIGN",
                requested_data={"successor_person_id": NABIL},
                reason="Manager keeps the release bot running under his sponsorship.",
                evidence_ids=agent_evidence,
            )
        elif action["resource_key"] == RELEASE_BOT_CREDENTIAL:
            action.update(
                action_type="DOWNSCOPE",
                requested_data={"successor_person_id": NABIL, "permission": "read"},
                reason="Rotate the deploy key to read-only under the new sponsor.",
                evidence_ids=agent_evidence,
            )
        revised.append(action)
    return revised


def rehearse(executor: str) -> dict[str, Any]:
    from app.main import app

    if executor == "offline":
        # Render's n8n cannot reach a backend on this laptop, so apply actions
        # in-process exactly as the n8n mock branch would.
        from app.demo.offline_executor import dispatch_offline
        from app.execution import service as execution_service

        execution_service.dispatch_to_n8n = dispatch_offline

    client = TestClient(app)
    timings: dict[str, float] = {}
    summary: dict[str, Any] = {"executor": executor}

    started = time.perf_counter()
    case = _call(client, "POST", "/cases", {
        "case_type": "OFFBOARDING",
        "subject_person_id": ARIF,
        "created_by_id": FARHANA,
        "priority": "HIGH",
        "case_facts": CASE_FACTS,
    })
    case_id = case["id"]
    triage = _call(client, "POST", f"/cases/{case_id}/triage")
    if not triage["ready_for_planning"]:
        raise RehearsalError(f"Triage not ready: {triage}")
    context = _call(client, "GET", f"/cases/{case_id}/policy-context")
    evidence = _evidence_by_code(context)
    summary["retrieved_policies"] = sorted(evidence)

    # Scene 2: the AI drafts the plan.
    t0 = time.perf_counter()
    ai_plan = _call(client, "POST", f"/cases/{case_id}/offboarding/plan")
    timings["scene2_ai_plan_s"] = round(time.perf_counter() - t0, 1)
    ai_actions = _flatten(ai_plan["plan_data"])
    summary["ai_plan"] = [
        f"{a['sequence']}. {a['action_type']} {a['resource_key']} {a['evidence_ids']}"
        for a in ai_actions
    ]
    summary["ai_bot_decision"] = next(
        (a["action_type"] for a in ai_actions if a["resource_key"] == RELEASE_BOT), None
    )
    summary["targeted_questions"] = len(ai_plan["plan_data"].get("targeted_questions", []))

    # Scene 3: Nabil corrects the plan; the revision goes to him for approval.
    revised_actions = _nabil_revision(ai_actions, evidence)
    revision = _call(client, "POST", f"/plans/{ai_plan['id']}/revise", {
        "plan_data": {
            "summary": "Offboard Arif; keep Aurora Release Bot read-only under Nabil.",
            "actions": revised_actions,
            "warnings": [],
        },
        "correction_summary": CORRECTIONS[summary["ai_bot_decision"]],
    })
    _call(client, "POST", f"/approvals/{revision['approval_id']}/decision", {
        "decided_by": NABIL,
        "decision": "APPROVED",
        "comment": "Approved with my correction.",
    })

    # Scene 4: execution and verification, timed like the on-stage stopwatch.
    t0 = time.perf_counter()
    execution = _call(client, "POST", f"/plans/{revision['id']}/execute")
    timings["scene4_execute_and_verify_s"] = round(time.perf_counter() - t0, 1)
    summary["execution"] = execution

    # The correction becomes a lesson once every action is verified.
    t0 = time.perf_counter()
    candidate = _call(client, "POST", f"/cases/{case_id}/learning/candidate", {"assigned_to": TAHMID})
    decision = _call(client, "POST", f"/learning-approvals/{candidate['approval_id']}/decision", {
        "decided_by": TAHMID,
        "decision": "APPROVED",
        "comment": "Good lesson for release bots.",
    })
    indexed = _call(client, "POST", f"/learning/{candidate['learning_record_id']}/index")
    timings["scene3_lesson_s"] = round(time.perf_counter() - t0, 1)
    summary["lesson"] = {
        "recommended_action": candidate["candidate"].get("recommended_action"),
        "status": decision["learning_status"],
        "indexed": indexed,
    }

    bot = _call(client, "GET", f"/agents/{RELEASE_BOT}")
    credential = _call(client, "GET", f"/agents/{RELEASE_BOT}/grants")
    summary["bot_after"] = {
        "sponsor": bot["sponsor"]["name"] if bot["sponsor"] else None,
        "orphan": bot["orphan"],
        "credential": [(c["resource_key"], c["status"], c["sponsor_id"] == NABIL) for c in credential],
    }
    summary["case_id"] = case_id
    timings["total_s"] = round(time.perf_counter() - started, 1)
    summary["timings"] = timings
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Rehearse demo scenes 2-4.")
    parser.add_argument("--executor", choices=["offline", "n8n"], default="offline")
    args = parser.parse_args()
    print(json.dumps(rehearse(args.executor), indent=2, default=str))


if __name__ == "__main__":
    main()
