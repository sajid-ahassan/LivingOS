"""Does an approved lesson change the next plan? Measured, not assumed.

Three real Engineering agents from the demo company are planned twice as if
their sponsor were leaving (with the sponsor's whole inventory): once with no lessons, once with the approved
lesson from the hero story (a manager kept the release bot running under
himself, read-only). A plan "matches the correction" when the agent is
REASSIGNED and its credential is DOWNSCOPED to read, which is what the
manager had to change by hand.

Nothing is written: the probe case and its resources stay out of the
session, and plan attempts are not recorded, so the demo metrics are
untouched. The lesson text is fixed so the AI cache answers OFFLINE.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ActionType, CaseState, CaseType, ResourceType
from app.learning.lessons import LessonContext, is_lesson_evidence
from app.models import Case, CompanyResource, Person


NABIL = UUID("22222222-2222-4222-8222-222222222222")

PROBE_AGENTS = (
    "agent:helios-deploy-bot",
    "agent:billing-migration-agent",
    "agent:on-call-incident-bot",
)

PROBE_LESSON_ID = UUID("00000000-0000-4000-8000-00000000e001")
PROBE_LESSON = LessonContext(
    evidence_id=f"MEM-{PROBE_LESSON_ID}-C0",
    learning_id=PROBE_LESSON_ID,
    text=(
        "When a departing engineer sponsors a release or deployment agent that an "
        "active project still depends on, do not shut the agent down. Reassign it "
        "to the departing employee's manager and rotate its credential to "
        "read-only (DOWNSCOPE) until the new sponsor re-approves write access."
    ),
    credential_permission="read",
)


def _probe(db: Session, agent_key: str):
    agent = db.scalar(
        select(CompanyResource).where(CompanyResource.resource_key == agent_key)
    )
    if agent is None:
        return None
    credential_key = (agent.details_data or {}).get("credential_key")
    credential = db.scalar(
        select(CompanyResource).where(CompanyResource.resource_key == credential_key)
    )
    sponsor = db.get(Person, agent.person_id)
    if credential is None or sponsor is None:
        return None
    successor = sponsor.manager_id or NABIL
    case = Case(
        id=uuid5(NAMESPACE_URL, f"livingops:lesson-probe:{agent_key}"),
        case_type=CaseType.OFFBOARDING,
        status=CaseState.PLANNING,
        subject_person_id=sponsor.id,
        created_by_id=sponsor.id,
        case_facts={
            "last_working_day": "2026-12-26",
            "manager_id": str(successor),
            "successor_person_id": str(successor),
            "department": sponsor.department,
            "job_title": sponsor.job_title,
        },
    )
    # The sponsor's whole inventory, as in a real offboarding; read only.
    resources = list(
        db.scalars(
            select(CompanyResource)
            .where(CompanyResource.person_id == sponsor.id)
            .order_by(CompanyResource.resource_key)
        )
    )
    return case, agent, credential, resources


def _outcome(plan, agent_key: str, credential_key: str) -> dict[str, Any]:
    actions = [*plan.revocations, *plan.asset_returns, *plan.reassignments]
    by_key = {action.resource_key: action for action in actions}
    agent_action = by_key.get(agent_key)
    credential_action = by_key.get(credential_key)
    matches = bool(
        agent_action
        and agent_action.action_type == ActionType.REASSIGN
        and credential_action
        and credential_action.action_type == ActionType.DOWNSCOPE
        and credential_action.requested_data.get("permission") == "read"
    )
    return {
        "agent_action": agent_action.action_type.value if agent_action else None,
        "credential_action": (
            credential_action.action_type.value if credential_action else None
        ),
        "matches_correction": matches,
        "policy_cited_every_step": all(
            any(not is_lesson_evidence(item) for item in action.evidence_ids)
            for action in actions
        ),
        "lesson_cited": any(
            is_lesson_evidence(item)
            for action in actions
            for item in action.evidence_ids
        ),
    }


def _rate(part: int, whole: int) -> float | None:
    return round(100.0 * part / whole, 1) if whole else None


def lesson_reuse(db: Session) -> dict[str, Any]:
    from app.offboarding.graph_runner import generate_offboarding_plan_via_graph

    probes = []
    for agent_key in PROBE_AGENTS:
        probe = _probe(db, agent_key)
        if probe is None:
            continue
        case, agent, credential, resources = probe
        row: dict[str, Any] = {
            "agent": (agent.details_data or {}).get("agent_name") or agent_key,
        }
        for label, lessons in (("without_lesson", []), ("with_lesson", [PROBE_LESSON])):
            try:
                plan, _ = generate_offboarding_plan_via_graph(
                    db,
                    case,
                    resources,
                    lessons=lessons,
                    record_attempt=False,
                )
                row[label] = _outcome(plan, agent.resource_key, credential.resource_key)
            except Exception as exc:  # noqa: BLE001 - a failed plan is a result
                row[label] = {"error": str(exc)[:300], "matches_correction": False}
        probes.append(row)
    db.rollback()

    n = len(probes)
    without = sum(1 for row in probes if row["without_lesson"].get("matches_correction"))
    with_lesson = sum(1 for row in probes if row["with_lesson"].get("matches_correction"))
    policy_ok = sum(
        1 for row in probes if row["with_lesson"].get("policy_cited_every_step")
    )
    cited = sum(1 for row in probes if row["with_lesson"].get("lesson_cited"))
    return {
        "n": n,
        "lesson": PROBE_LESSON.evidence_id,
        "matches_correction_without_lesson_pct": _rate(without, n),
        "matches_correction_with_lesson_pct": _rate(with_lesson, n),
        "lesson_cited_pct": _rate(cited, n),
        "policy_cited_every_step_with_lesson_pct": _rate(policy_ok, n),
        "probes": probes,
        "note": (
            "Lessons are advisory: every step must still cite policy evidence, "
            "and only APPROVED lessons linked to CURRENT policy reach the planner."
        ),
    }
