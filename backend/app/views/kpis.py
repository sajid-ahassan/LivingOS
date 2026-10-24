"""Dashboard KPIs, measured on the demo company and labelled as such.

Pure functions over loaded rows so they are easy to test and always computed
the same way.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.agents.rules import orphan_reasons
from app.enums import ActionState, CaseState, CaseType, EmploymentStatus, ResourceType
from app.models import Case, CaseAction, CompanyResource, Person
from app.offboarding.rules import TERMINAL_RESOURCE_STATES


KPI_LABEL = "Measured on the Nexora Labs demo company (simulated operational comparison)."
HUMAN_ACCESS_TYPES = {
    ResourceType.EMAIL_ACCOUNT,
    ResourceType.GITHUB_ACCESS,
    ResourceType.LAPTOP,
    ResourceType.TRAINING,
}
ACCESS_TYPES = {ResourceType.EMAIL_ACCOUNT, ResourceType.GITHUB_ACCESS,
                ResourceType.AI_AGENT, ResourceType.AGENT_CREDENTIAL}


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def ownership(people: Iterable[Person], resources: Iterable[CompanyResource], now: datetime) -> dict[str, Any]:
    people_by_id = {person.id: person for person in people}
    live = [r for r in resources if r.status not in TERMINAL_RESOURCE_STATES]

    human = [r for r in live if r.resource_type in HUMAN_ACCESS_TYPES]
    human_owned = [
        r for r in human
        if (owner := people_by_id.get(r.person_id))
        and owner.employment_status in {EmploymentStatus.ACTIVE, EmploymentStatus.CANDIDATE}
    ]
    agents = [r for r in live if r.resource_type == ResourceType.AI_AGENT]
    orphans = [a for a in agents if orphan_reasons(a, people_by_id.get(a.person_id), now)]
    grants = [
        r for r in live
        if r.resource_type == ResourceType.AGENT_CREDENTIAL
        and (r.details_data or {}).get("kind") == "temporary_grant"
    ]
    expiring_agents = [a for a in agents if (a.details_data or {}).get("expires_at")]
    return {
        "human_access_with_active_owner_pct": _pct(len(human_owned), len(human)),
        "agents_with_active_sponsor_pct": _pct(len(agents) - len(orphans), len(agents)),
        "orphan_agents": len(orphans),
        "agents": len(agents),
        # Time-limited = agents with an expiry plus active temporary grants.
        "agent_access_time_limited": len(expiring_agents) + len(grants),
        "agent_access_standing": len(agents) - len(expiring_agents),
    }


def policy_reasons(actions: Iterable[CaseAction]) -> dict[str, Any]:
    executed = [a for a in actions if a.status not in {ActionState.PENDING, ActionState.SKIPPED}]
    with_reason = [
        a for a in executed
        if (a.requested_data or {}).get("evidence_ids") and (a.requested_data or {}).get("reason")
    ]
    return {
        "access_changes_through_livingops": len(executed),
        "with_policy_reason_pct": _pct(len(with_reason), len(executed)),
    }


def latest_offboarding(
    cases: Iterable[Case],
    actions_by_case: dict,
    verified_at: dict,
    approvals_by_case: dict,
) -> dict[str, Any] | None:
    """Termination-to-all-access-closed time and manual steps saved, for the
    most recently completed offboarding."""
    completed = sorted(
        (c for c in cases if c.case_type == CaseType.OFFBOARDING and c.status == CaseState.COMPLETED),
        key=lambda c: c.updated_at,
        reverse=True,
    )
    for case in completed:
        access_actions = [
            a for a in actions_by_case.get(case.id, [])
            if a.status == ActionState.VERIFIED and a.resource_type in ACCESS_TYPES
        ]
        times = [verified_at[a.id] for a in access_actions if a.id in verified_at]
        if not times:
            continue
        all_actions = [a for a in actions_by_case.get(case.id, []) if a.status == ActionState.VERIFIED]
        return {
            "case_id": str(case.id),
            "opened_at": case.created_at.isoformat(),
            "all_access_closed_at": max(times).isoformat(),
            "minutes_to_close_all_access": round((max(times) - case.created_at).total_seconds() / 60, 1),
            "automated_steps": len(all_actions),
            "human_approvals": approvals_by_case.get(case.id, 0),
        }
    return None
