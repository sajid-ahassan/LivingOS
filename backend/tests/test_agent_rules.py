from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.agents.rules import (
    ORPHAN_EXPIRED,
    ORPHAN_NO_SPONSOR,
    ORPHAN_SPONSOR_DEPARTING,
    ORPHAN_SPONSOR_INACTIVE,
    orphan_reasons,
)
from app.cases.schemas import CasePolicyContextResponse, PolicyEvidenceResponse
from app.enums import (
    ActionType,
    AppRole,
    CaseType,
    EmploymentStatus,
    ResourceState,
    ResourceType,
)
from app.mock_company.service import MUTATION_RESOURCE_TYPES
from app.models import Case, CompanyResource, Person
from app.offboarding.graph_runner import _validate_execution_plan
from app.offboarding.rules import (
    allowed_offboarding_actions,
    safe_resource_metadata,
    validate_access_evidence,
    validate_agent_coverage,
)
from app.offboarding.schemas import OffboardingPlan
from app.planning.schemas import GeneratedCasePlan, PlannedAction
from app.planning.validation import (
    GeneratedPlanValidationError,
    validate_generated_plan,
)
from app.resource_rules import action_moves_owner, target_resource_state


NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)

AGENT_KEY = "agent:aurora-release-bot"
CREDENTIAL_KEY = "credential:aurora-release-bot"
GITHUB_KEY = "github:aurora:arif"

ACCESS_EVIDENCE = "POL-ACCESS-V1-C2"
AGENT_EVIDENCE = "POL-AGENT-V1-C1"
OFFBOARDING_EVIDENCE = "POL-OFFBOARDING-V1-C0"


def _person(name: str, status: EmploymentStatus) -> Person:
    return Person(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}@nexora.demo",
        app_role=AppRole.EMPLOYEE,
        employment_status=status,
    )


ARIF = _person("Arif", EmploymentStatus.DEPARTING)
NABIL = _person("Nabil", EmploymentStatus.ACTIVE)
RAFI = _person("Rafi", EmploymentStatus.DEPARTING)
PEOPLE = {person.id: person for person in (ARIF, NABIL, RAFI)}


def _get_person(person_id):
    return PEOPLE.get(person_id)


class FakeDb:
    def get(self, _model, person_id):
        return PEOPLE.get(person_id)


def _agent(**details) -> CompanyResource:
    return CompanyResource(
        person_id=ARIF.id,
        resource_type=ResourceType.AI_AGENT,
        resource_key=AGENT_KEY,
        status=details.pop("status", ResourceState.ACTIVE),
        details_data={
            "agent_name": "Aurora Release Bot",
            "purpose": "release tags and changelog for Aurora",
            "scopes": [{"system": "github", "resource": "aurora", "permission": "write"}],
            "credential_key": CREDENTIAL_KEY,
            "mcp_api_key_hash": "never-shown",
            **details,
        },
        idempotency_key="seed:agent",
    )


def _credential() -> CompanyResource:
    return CompanyResource(
        person_id=ARIF.id,
        resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key=CREDENTIAL_KEY,
        status=ResourceState.ACTIVE,
        details_data={"key_id": 0},
        idempotency_key="seed:credential",
    )


def _github() -> CompanyResource:
    return CompanyResource(
        person_id=ARIF.id,
        resource_type=ResourceType.GITHUB_ACCESS,
        resource_key=GITHUB_KEY,
        status=ResourceState.ACTIVE,
        details_data={},
        idempotency_key="seed:github",
    )


def _action(
    sequence: int,
    action_type: ActionType,
    resource_type: ResourceType,
    resource_key: str,
    successor=None,
    evidence=(ACCESS_EVIDENCE, AGENT_EVIDENCE),
) -> PlannedAction:
    requested_data = {}
    if successor is not None:
        requested_data["successor_person_id"] = str(successor.id)
    return PlannedAction(
        sequence=sequence,
        action_type=action_type,
        resource_type=resource_type,
        resource_key=resource_key,
        requested_data=requested_data,
        reason="Sponsor is leaving the company.",
        evidence_ids=list(evidence),
    )


def _ai_version() -> list[PlannedAction]:
    """Scene 2: the planner shuts the bot down."""
    return [
        _action(1, ActionType.REVOKE, ResourceType.GITHUB_ACCESS, GITHUB_KEY,
                evidence=(ACCESS_EVIDENCE,)),
        _action(2, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY),
        _action(3, ActionType.REVOKE, ResourceType.AGENT_CREDENTIAL, CREDENTIAL_KEY),
    ]


def _nabil_version() -> list[PlannedAction]:
    """Scene 3: the manager keeps the bot, read-only, under himself."""
    return [
        _action(1, ActionType.REVOKE, ResourceType.GITHUB_ACCESS, GITHUB_KEY,
                evidence=(ACCESS_EVIDENCE,)),
        _action(2, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, NABIL),
        _action(3, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL,
                CREDENTIAL_KEY, NABIL),
    ]


def _resources() -> list[CompanyResource]:
    return [_github(), _agent(), _credential()]


def _policy_context(codes=("ACCESS", "AGENT", "OFFBOARDING")) -> CasePolicyContextResponse:
    evidence_by_code = {
        "ACCESS": ACCESS_EVIDENCE,
        "AGENT": AGENT_EVIDENCE,
        "OFFBOARDING": OFFBOARDING_EVIDENCE,
    }
    return CasePolicyContextResponse(
        case_id=uuid4(),
        search_query="offboarding",
        evidence=[
            PolicyEvidenceResponse(
                evidence_id=evidence_by_code[code],
                policy_code=code,
                version_number=1,
                text=f"{code} clause",
                score=1.0,
            )
            for code in codes
        ],
    )


def _coverage(actions):
    return validate_agent_coverage(
        actions,
        _resources(),
        subject_person_id=ARIF.id,
        get_person=_get_person,
    )


# Orphan detection


def test_agent_with_active_sponsor_is_not_orphan():
    assert orphan_reasons(_agent(), NABIL, NOW) == []


@pytest.mark.parametrize(
    ("sponsor", "reason"),
    [
        (None, ORPHAN_NO_SPONSOR),
        (ARIF, ORPHAN_SPONSOR_DEPARTING),
        (_person("Gone", EmploymentStatus.INACTIVE), ORPHAN_SPONSOR_INACTIVE),
    ],
)
def test_agent_sponsor_problems_make_it_orphan(sponsor, reason):
    assert orphan_reasons(_agent(), sponsor, NOW) == [reason]


def test_expired_agent_is_orphan():
    agent = _agent(expires_at=(NOW - timedelta(minutes=1)).isoformat())
    assert orphan_reasons(agent, NABIL, NOW) == [ORPHAN_EXPIRED]


def test_future_expiry_is_not_orphan():
    agent = _agent(expires_at=(NOW + timedelta(hours=2)).isoformat())
    assert orphan_reasons(agent, NABIL, NOW) == []


def test_orphan_reasons_combine():
    agent = _agent(expires_at="2026-10-01T00:00:00Z")
    assert orphan_reasons(agent, ARIF, NOW) == [
        ORPHAN_SPONSOR_DEPARTING,
        ORPHAN_EXPIRED,
    ]


def test_revoked_agent_is_not_orphan():
    agent = _agent(status=ResourceState.REVOKED)
    assert orphan_reasons(agent, None, NOW) == []


def test_orphan_check_rejects_non_agents():
    with pytest.raises(ValueError):
        orphan_reasons(_credential(), NABIL, NOW)


# Allowed offboarding actions


def test_agent_offboarding_choices():
    assert allowed_offboarding_actions(_agent()) == {
        ActionType.REASSIGN,
        ActionType.REVOKE,
    }
    assert allowed_offboarding_actions(_credential()) == {
        ActionType.REASSIGN,
        ActionType.DOWNSCOPE,
        ActionType.REVOKE,
    }


def test_retired_agent_needs_no_action():
    assert allowed_offboarding_actions(_agent(status=ResourceState.REVOKED)) == set()


def test_human_github_access_still_requires_revoke_only():
    assert allowed_offboarding_actions(_github()) == {ActionType.REVOKE}


# Agent coverage


def test_ai_version_revoking_bot_is_valid():
    assert _coverage(_ai_version()) == []


def test_nabil_version_reassign_and_downscope_is_valid():
    assert _coverage(_nabil_version()) == []


def test_missing_agent_action_fails():
    actions = [_nabil_version()[0], _nabil_version()[2]]
    errors = _coverage(actions)
    assert any(AGENT_KEY in error for error in errors)


def test_revoked_agent_needs_revoked_credential():
    actions = [
        _action(1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY),
        _action(2, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL,
                CREDENTIAL_KEY, NABIL),
    ]
    assert any("must be revoked too" in error for error in _coverage(actions))


def test_reassigned_agent_cannot_have_revoked_credential():
    actions = [
        _action(1, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, NABIL),
        _action(2, ActionType.REVOKE, ResourceType.AGENT_CREDENTIAL, CREDENTIAL_KEY),
    ]
    assert any("REASSIGN or DOWNSCOPE" in error for error in _coverage(actions))


def test_credential_must_follow_agent_successor():
    other = _person("Tahmid", EmploymentStatus.ACTIVE)
    PEOPLE[other.id] = other
    try:
        actions = [
            _action(1, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, NABIL),
            _action(2, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL,
                    CREDENTIAL_KEY, other),
        ]
        assert any("same successor" in error for error in _coverage(actions))
    finally:
        del PEOPLE[other.id]


def test_departing_successor_is_rejected():
    actions = [
        _action(1, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, RAFI),
        _action(2, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL,
                CREDENTIAL_KEY, RAFI),
    ]
    assert any("must be ACTIVE" in error for error in _coverage(actions))


def test_sponsor_cannot_be_own_successor():
    actions = [
        _action(1, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, ARIF),
        _action(2, ActionType.REVOKE, ResourceType.AGENT_CREDENTIAL, CREDENTIAL_KEY),
    ]
    assert any("cannot keep" in error for error in _coverage(actions))


def test_downscope_in_offboarding_needs_successor():
    actions = [
        _action(1, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, NABIL),
        _action(2, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL, CREDENTIAL_KEY),
    ]
    assert any("requires a valid successor" in error for error in _coverage(actions))


def test_downscope_is_not_valid_for_the_agent_itself():
    actions = [
        _action(1, ActionType.DOWNSCOPE, ResourceType.AI_AGENT, AGENT_KEY, NABIL),
        _action(2, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL,
                CREDENTIAL_KEY, NABIL),
    ]
    assert any("not a valid offboarding action" in error for error in _coverage(actions))


# ACCESS evidence linking


def test_agent_steps_citing_access_and_agent_pass():
    assert validate_access_evidence(_nabil_version(), _policy_context()) == []


def test_agent_step_without_access_evidence_fails():
    actions = [
        _action(1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY,
                evidence=(AGENT_EVIDENCE,)),
    ]
    errors = validate_access_evidence(actions, _policy_context())
    assert errors == [f"Agent step {AGENT_KEY} must cite ACCESS policy evidence."]


def test_agent_step_must_cite_agent_policy_when_retrieved():
    actions = [
        _action(1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY,
                evidence=(ACCESS_EVIDENCE,)),
    ]
    errors = validate_access_evidence(actions, _policy_context())
    assert errors == [f"Agent step {AGENT_KEY} must cite AGENT policy evidence."]
    assert validate_access_evidence(actions, _policy_context(("ACCESS",))) == []


def test_missing_access_retrieval_is_reported_clearly():
    actions = [_action(1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY,
                       evidence=(OFFBOARDING_EVIDENCE,))]
    errors = validate_access_evidence(actions, _policy_context(("OFFBOARDING",)))
    assert errors == [
        f"No ACCESS policy evidence was retrieved, so agent step {AGENT_KEY} "
        "cannot be justified."
    ]


def test_human_steps_do_not_need_access_evidence():
    actions = [_action(1, ActionType.REVOKE, ResourceType.GITHUB_ACCESS, GITHUB_KEY,
                       evidence=(OFFBOARDING_EVIDENCE,))]
    assert validate_access_evidence(actions, _policy_context()) == []


# Manager revision path (validate_generated_plan)


def _offboarding_case() -> Case:
    return Case(
        id=uuid4(),
        case_type=CaseType.OFFBOARDING,
        subject_person_id=ARIF.id,
        case_facts={},
    )


def _validate_revision(actions):
    validate_generated_plan(
        GeneratedCasePlan(summary="Offboard Arif and his agent.", actions=actions),
        case=_offboarding_case(),
        policy_context=_policy_context(),
        resources=_resources(),
        get_person=_get_person,
    )


def test_revision_with_nabil_correction_passes():
    _validate_revision(_nabil_version())


def test_revision_cannot_drop_the_agent():
    actions = [_nabil_version()[0]]
    with pytest.raises(GeneratedPlanValidationError, match=AGENT_KEY):
        _validate_revision(actions)


def test_revision_cannot_downscope_a_leavers_github_access():
    actions = _nabil_version()
    actions[0] = _action(1, ActionType.DOWNSCOPE, ResourceType.GITHUB_ACCESS,
                         GITHUB_KEY, evidence=(ACCESS_EVIDENCE,))
    with pytest.raises(GeneratedPlanValidationError, match="must be one of"):
        _validate_revision(actions)


# Planner path (offboarding graph validation)


def _offboarding_plan(revocations, reassignments) -> OffboardingPlan:
    return OffboardingPlan(
        summary="Offboard Arif and his agent.",
        revocations=revocations,
        reassignments=reassignments,
    )


def _graph_errors(plan: OffboardingPlan) -> list[str]:
    context = _policy_context()
    return _validate_execution_plan(
        FakeDb(),
        _offboarding_case(),
        plan,
        _resources(),
        {item.evidence_id for item in context.evidence},
        context,
    )


def test_graph_accepts_agent_offboarding_plan():
    ai, nabil = _ai_version(), _nabil_version()
    assert _graph_errors(_offboarding_plan(ai, [])) == []
    assert _graph_errors(_offboarding_plan(nabil[:1], nabil[1:])) == []


def test_graph_rejects_plan_that_forgets_the_agent():
    plan = _offboarding_plan(_ai_version()[:1], [])
    errors = _graph_errors(plan)
    assert any(AGENT_KEY in error for error in errors)
    assert any(CREDENTIAL_KEY in error for error in errors)


# Shared resource rules and mock company


def test_reassigned_agent_stays_active_but_work_item_is_finished():
    assert target_resource_state(ActionType.REASSIGN, ResourceType.AI_AGENT) == ResourceState.ACTIVE
    assert target_resource_state(ActionType.REASSIGN, ResourceType.WORK_ITEM) == ResourceState.REASSIGNED
    assert target_resource_state(ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL) == ResourceState.ACTIVE


def test_downscope_moves_owner_only_with_successor():
    assert action_moves_owner(ActionType.REASSIGN, {})
    assert action_moves_owner(ActionType.DOWNSCOPE, {"successor_person_id": str(NABIL.id)})
    assert not action_moves_owner(ActionType.DOWNSCOPE, {})
    assert not action_moves_owner(ActionType.REVOKE, {"successor_person_id": str(NABIL.id)})


def test_mock_company_accepts_agent_actions():
    assert ResourceType.AI_AGENT in MUTATION_RESOURCE_TYPES[ActionType.REASSIGN]
    assert ResourceType.AGENT_CREDENTIAL in MUTATION_RESOURCE_TYPES[ActionType.REVOKE]
    assert MUTATION_RESOURCE_TYPES[ActionType.DOWNSCOPE] == {
        ResourceType.AGENT_CREDENTIAL,
        ResourceType.GITHUB_ACCESS,
    }


def test_planner_sees_agent_metadata_but_no_secrets():
    metadata = safe_resource_metadata(_agent())
    assert metadata["credential_key"] == CREDENTIAL_KEY
    assert metadata["purpose"]
    assert "mcp_api_key_hash" not in metadata
    assert "key_id" not in safe_resource_metadata(_credential())
