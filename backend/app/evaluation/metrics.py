"""Evaluation panel metrics. Real numbers only, each with its sample size.

- plan_generation: AI plan attempts recorded by the planners (first-pass
  valid, valid after the one repair, failed to human review).
- evidence: plan steps that cite policy evidence resolving to a real version.
- retrieval: recall@1 and @3 of the expected policy on seeded questions.
- guardian: recall and false impacts of the deterministic re-check on a
  seeded scenario set (no LLM involved, so it must be exact).
- execution: verified completion, retries that recovered, replays the
  idempotency guard absorbed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    ActionState,
    AppRole,
    EmploymentStatus,
    ResourceState,
    ResourceType,
)
from app.evaluation.attempts import PLAN_GENERATION_ATTEMPT
from app.evidence.explanation import POLICY_EVIDENCE
from app.models import AuditEvent, CaseAction, CompanyResource, Person, PolicyVersion
from app.policy_guardian.resource_rules import (
    RULE_CONFIDENTIAL_WRITE,
    RULE_SPONSOR_RECERTIFY,
    ResourceContext,
    evaluate_resources,
    newly_added_rules,
)


RETRIEVAL_QUESTIONS = [
    ("Remove repository access no later than the employee's final working day", "ACCESS"),
    ("Production access during initial onboarding", "ACCESS"),
    ("Return the company laptop when an employee leaves", "EQUIPMENT"),
    ("Which laptop does a new engineer receive", "EQUIPMENT"),
    ("Reassign open work and handover documents before leaving", "OFFBOARDING"),
    ("What happens to an AI agent when its human sponsor leaves", "AGENT"),
    ("Can an agent get write access to a confidential repository", "AGENT"),
    ("Agent read access approved automatically with expiry", "AGENT"),
]


def _rate(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def plan_generation(db: Session) -> dict[str, Any]:
    attempts = [
        event.after_data or {}
        for event in db.scalars(
            select(AuditEvent).where(AuditEvent.event_type == PLAN_GENERATION_ATTEMPT)
        )
    ]
    n = len(attempts)
    first = sum(1 for item in attempts if item.get("first_pass_valid"))
    valid = sum(1 for item in attempts if item.get("valid"))
    return {
        "n": n,
        "first_pass_valid_pct": _rate(first, n),
        "valid_after_repair_pct": _rate(valid, n),
        "sent_to_human_review": n - valid,
    }


def evidence_coverage(db: Session) -> dict[str, Any]:
    versions = {
        (version.policy_code, version.version_number)
        for version in db.scalars(select(PolicyVersion))
    }
    actions = list(db.scalars(select(CaseAction)))
    cited = 0
    for action in actions:
        for evidence_id in (action.requested_data or {}).get("evidence_ids") or []:
            match = POLICY_EVIDENCE.match(evidence_id)
            if match and (match["code"], int(match["version"])) in versions:
                cited += 1
                break
    return {"n": len(actions), "steps_with_policy_evidence_pct": _rate(cited, len(actions))}


def retrieval_recall(db: Session) -> dict[str, Any]:
    from app.rag.hybrid_retriever import search_current_policies_hybrid

    hits_at_1 = hits_at_3 = 0
    misses = []
    for question, expected in RETRIEVAL_QUESTIONS:
        codes = [r.policy_code for r in search_current_policies_hybrid(db, query=question, top_k=3)]
        hits_at_1 += codes[:1] == [expected]
        hits_at_3 += expected in codes[:3]
        if codes[:1] != [expected]:
            misses.append({"question": question, "expected": expected, "got": codes})
    n = len(RETRIEVAL_QUESTIONS)
    return {
        "n": n,
        "recall_at_1_pct": _rate(hits_at_1, n),
        "recall_at_3_pct": _rate(hits_at_3, n),
        "top1_misses": misses,
    }


def _guardian_case(
    name: str,
    resource_type: ResourceType,
    details: dict,
    trained: bool,
    expected: str | None,
) -> tuple[ResourceContext, str | None]:
    sponsor = Person(
        id=uuid4(), name="Sponsor", email=f"{uuid4().hex[:8]}@nexora.demo",
        app_role=AppRole.EMPLOYEE, employment_status=EmploymentStatus.ACTIVE,
    )
    resource = CompanyResource(
        id=uuid4(), person_id=sponsor.id, resource_type=resource_type,
        resource_key=name, status=ResourceState.ACTIVE, details_data=details,
        idempotency_key=name,
    )
    training = frozenset({"SECURITY-CONFIDENTIAL"}) if trained else frozenset()
    return ResourceContext(resource, sponsor, training), expected


def guardian_scenarios() -> list[tuple[ResourceContext, str | None]]:
    previous = {"previous_person_id": str(uuid4())}
    return [
        _guardian_case("cred:write-untrained", ResourceType.AGENT_CREDENTIAL,
                       {"permission": "write", "repository": "aurora"}, False, RULE_CONFIDENTIAL_WRITE),
        _guardian_case("cred:write-trained", ResourceType.AGENT_CREDENTIAL,
                       {"permission": "write", "repository": "aurora"}, True, None),
        _guardian_case("cred:read-untrained", ResourceType.AGENT_CREDENTIAL,
                       {"permission": "read", "repository": "aurora"}, False, None),
        _guardian_case("cred:write-public-repo", ResourceType.AGENT_CREDENTIAL,
                       {"permission": "write", "repository": "helios"}, False, None),
        _guardian_case("agent:reassigned", ResourceType.AI_AGENT, previous, False, RULE_SPONSOR_RECERTIFY),
        _guardian_case("agent:never-reassigned", ResourceType.AI_AGENT, {}, False, None),
    ]


def guardian_accuracy(old_text: str, new_text: str) -> dict[str, Any]:
    scenarios = guardian_scenarios()
    findings = evaluate_resources(newly_added_rules(old_text, new_text), [c for c, _ in scenarios])
    found = {(f.resource.resource_key, f.rule_id) for f in findings}
    expected = {(c.resource.resource_key, rule) for c, rule in scenarios if rule}
    return {
        "n_scenarios": len(scenarios),
        "expected_impacts": len(expected),
        "recall_pct": _rate(len(found & expected), len(expected)),
        "false_impacts": len(found - expected),
    }


def execution_outcomes(db: Session) -> dict[str, Any]:
    actions = [
        action for action in db.scalars(select(CaseAction))
        if action.status not in {ActionState.PENDING, ActionState.SKIPPED}
    ]
    verified = sum(1 for a in actions if a.status == ActionState.VERIFIED)
    recovered = sum(1 for a in actions if a.status == ActionState.VERIFIED and a.attempt_count > 1)
    replays = sum(
        1 for a in actions
        if (a.result_data or {}).get("already_existed")
        or ((a.result_data or {}).get("details") or {}).get("replayed")
    )
    return {
        "n": len(actions),
        "verified_completion_pct": _rate(verified, len(actions)),
        "retries_recovered": recovered,
        "replays_absorbed": replays,
    }


def run_all(db: Session, *, access_v1: str, access_v2: str, demo_mode: str) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": demo_mode,
        "company": "Nexora Labs (fictional demo company)",
        "note": "Measured on the demo company; numbers are reported as found.",
        "plan_generation": plan_generation(db),
        "evidence": evidence_coverage(db),
        "retrieval": retrieval_recall(db),
        "guardian": guardian_accuracy(access_v1, access_v2),
        "execution": execution_outcomes(db),
    }
