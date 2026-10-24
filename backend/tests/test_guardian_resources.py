from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agents.service import build_workforce_graph, violating_agent_keys
from app.enums import (
    AppRole,
    EmploymentStatus,
    ImpactRecommendedAction,
    ImpactState,
    ResourceState,
    ResourceType,
    RiskLevel,
)
from app.models import Case, CasePlan, CompanyResource, Person, PolicyImpact
from app.policy_guardian.resource_remediation import resolve_remediated_impact
from app.policy_guardian.resource_rules import (
    RULE_CONFIDENTIAL_WRITE,
    RULE_SPONSOR_RECERTIFY,
    ResourceContext,
    evaluate_resources,
    newly_added_rules,
)
from app.policy_guardian.service import _plan_contains_sensitive_access


SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"
ACCESS_V1 = (SEED_DIR / "access_policy_v1.md").read_text(encoding="utf-8")
ACCESS_V2 = (SEED_DIR / "access_policy_v2.md").read_text(encoding="utf-8")


def _person(name: str) -> Person:
    return Person(
        id=uuid4(), name=name, email=f"{name.lower()}@nexora.demo",
        app_role=AppRole.LINE_MANAGER, employment_status=EmploymentStatus.ACTIVE,
    )


NABIL = _person("Nabil")
ARIF = _person("Arif")


def _credential(permission: str, repository: str = "aurora", status=ResourceState.ACTIVE, key="credential:aurora-release-bot"):
    return CompanyResource(
        id=uuid4(), person_id=NABIL.id, resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key=key, status=status,
        details_data={"agent_key": "agent:aurora-release-bot", "permission": permission,
                      "repository": repository},
        idempotency_key=f"seed:{key}",
    )


def _agent(previous=ARIF, recertified_for=None):
    details = {"agent_name": "Aurora Release Bot", "credential_key": "credential:aurora-release-bot"}
    if previous is not None:
        details["previous_person_id"] = str(previous.id)
    if recertified_for is not None:
        details["recertified_for_sponsor"] = str(recertified_for.id)
    return CompanyResource(
        id=uuid4(), person_id=NABIL.id, resource_type=ResourceType.AI_AGENT,
        resource_key="agent:aurora-release-bot", status=ResourceState.ACTIVE,
        details_data=details, idempotency_key="seed:agent",
    )


def _context(resource, training=()):
    return ResourceContext(resource=resource, sponsor=NABIL, sponsor_training=frozenset(training))


def _v2_findings(*contexts):
    return evaluate_resources(newly_added_rules(ACCESS_V1, ACCESS_V2), contexts)


# Which rules a policy change switches on


def test_access_v2_adds_both_agent_rules():
    rules = newly_added_rules(ACCESS_V1, ACCESS_V2)
    assert [rule.rule_id for rule in rules] == [RULE_CONFIDENTIAL_WRITE, RULE_SPONSOR_RECERTIFY]


def test_unchanged_or_reverted_policy_adds_no_rules():
    assert newly_added_rules(ACCESS_V2, ACCESS_V2) == []
    assert newly_added_rules(ACCESS_V1, ACCESS_V1) == []
    assert newly_added_rules(ACCESS_V2, ACCESS_V1) == []


def test_v2_seed_file_is_v1_plus_two_rules():
    assert "Version: 2" in ACCESS_V2
    v1_rules = [line for line in ACCESS_V1.splitlines() if line[:2] in {f"{n}." for n in range(1, 7)}]
    assert all(rule in ACCESS_V2 for rule in v1_rules)
    assert "7. An AI agent may hold write access" in ACCESS_V2
    assert "8. When an agent's sponsor changes" in ACCESS_V2


# Rule 7: write to a confidential repo needs a trained sponsor


def test_write_grant_without_sponsor_training_is_high_and_downscoped():
    [finding] = _v2_findings(_context(_credential("write")))
    assert finding.rule_id == RULE_CONFIDENTIAL_WRITE
    assert finding.risk_level == RiskLevel.HIGH
    assert finding.recommended_action == ImpactRecommendedAction.REGENERATE
    assert "Nabil" in finding.explanation and "SECURITY-CONFIDENTIAL" in finding.explanation


def test_trained_sponsor_may_keep_write():
    assert _v2_findings(_context(_credential("write"), training={"SECURITY-CONFIDENTIAL"})) == []


def test_read_only_or_non_confidential_or_revoked_credentials_pass():
    assert _v2_findings(_context(_credential("read"))) == []
    assert _v2_findings(_context(_credential("write", repository="helios"))) == []
    assert _v2_findings(_context(_credential("write", status=ResourceState.REVOKED))) == []


# Rule 8: a new sponsor needs IT Owner re-certification


def test_reassigned_agent_without_recertification_needs_review():
    [finding] = _v2_findings(_context(_agent()))
    assert finding.rule_id == RULE_SPONSOR_RECERTIFY
    assert finding.recommended_action == ImpactRecommendedAction.REVIEW
    assert finding.risk_level == RiskLevel.MEDIUM


def test_recertified_for_current_sponsor_passes_but_not_for_old_one():
    assert _v2_findings(_context(_agent(recertified_for=NABIL))) == []
    assert len(_v2_findings(_context(_agent(recertified_for=ARIF)))) == 1


def test_agent_that_never_changed_sponsor_passes():
    assert _v2_findings(_context(_agent(previous=None))) == []


# The hero story: after scene 4 and scene 5, Access Policy V2 lands


def test_scene_six_flags_the_grant_and_the_bot_every_time():
    downscoped = _credential("read")                       # scene 4 result
    temporary_write = _credential("write", key="credential:aurora-release-bot:grant")  # scene 5
    bot = _agent()                                         # reassigned in scene 4
    contexts = [_context(downscoped), _context(temporary_write), _context(bot)]

    first = _v2_findings(*contexts)
    second = _v2_findings(*reversed(contexts))

    assert [(f.rule_id, f.resource.resource_key) for f in first] == [
        (RULE_CONFIDENTIAL_WRITE, "credential:aurora-release-bot:grant"),
        (RULE_SPONSOR_RECERTIFY, "agent:aurora-release-bot"),
    ]
    assert [(f.rule_id, f.resource.resource_key) for f in second] == [
        (f.rule_id, f.resource.resource_key) for f in first
    ]


def test_offboarding_plans_with_agents_count_as_sensitive():
    plan = CasePlan(plan_data={"reassignments": [{"resource_type": "AI_AGENT"}]})
    assert _plan_contains_sensitive_access(plan)
    assert not _plan_contains_sensitive_access(CasePlan(plan_data={"actions": [{"resource_type": "LAPTOP"}]}))


# Map highlight and closing the loop


def test_impacted_credential_highlights_its_agent_on_the_map():
    credential = _credential("write")
    agent = _agent()
    keys = violating_agent_keys([credential])
    assert keys == {"agent:aurora-release-bot"}

    graph = build_workforce_graph(
        [NABIL], [agent, credential], datetime(2026, 12, 26, tzinfo=timezone.utc), keys
    )
    assert graph.agents[0].policy_violation is True


class ImpactDb:
    def __init__(self, impact):
        self.impact = impact

    def get(self, _model, impact_id):
        return self.impact if impact_id == self.impact.id else None


def test_completed_remediation_case_resolves_its_impact():
    impact = PolicyImpact(id=uuid4(), status=ImpactState.REMEDIATING)
    owner = uuid4()
    case = Case(created_by_id=owner, case_facts={"policy_impact_id": str(impact.id)})
    resolve_remediated_impact(ImpactDb(impact), case)
    assert impact.status == ImpactState.RESOLVED
    assert impact.resolved_by == owner


def test_ordinary_cases_leave_impacts_alone():
    impact = PolicyImpact(id=uuid4(), status=ImpactState.OPEN)
    resolve_remediated_impact(ImpactDb(impact), Case(case_facts={}))
    assert impact.status == ImpactState.OPEN
