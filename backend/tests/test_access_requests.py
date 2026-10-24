from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.access_requests.auth import AgentAuthError, check_service_token, hash_agent_key
from app.access_requests.service import due_grants
from app.access_requests.tiers import RiskTier, decide_tier
from app.cases.schemas import CasePolicyContextResponse, PolicyEvidenceResponse
from app.enums import (
    ActionType,
    AppRole,
    CaseType,
    EmploymentStatus,
    ResourceState,
    ResourceType,
)
from app.main import app
from app.mock_company.service import CREATION_ACTIONS
from app.models import Case, CompanyResource, Person
from app.planning.schemas import GeneratedCasePlan, PlannedAction
from app.planning.validation import validate_generated_plan
from app.resource_rules import target_resource_state


NOW = datetime(2026, 12, 26, 11, 0, tzinfo=timezone.utc)


def _sponsor(status=EmploymentStatus.ACTIVE) -> Person:
    return Person(
        id=uuid4(), name="Nabil Chowdhury", email="nabil@nexora.demo",
        app_role=AppRole.LINE_MANAGER, employment_status=status,
    )


def _tier(permission, resource, minutes, sponsor=None):
    return decide_tier(
        permission=permission, resource=resource, duration_minutes=minutes,
        sponsor=sponsor if sponsor is not None else _sponsor(),
    )


# Risk tiers (rules, not the LLM)


def test_read_on_a_normal_repo_is_low_and_auto_approved():
    decision = _tier("read", "helios", 60)
    assert decision.tier == RiskTier.LOW
    assert decision.policy_rule == "AGENT-V1 rule 4"


def test_scene_five_two_hours_write_on_aurora_is_high():
    decision = _tier("write", "aurora", 120)
    assert decision.tier == RiskTier.HIGH
    assert "write access" in decision.reasons
    assert "aurora is a confidential repository" in decision.reasons


def test_read_on_a_confidential_repo_is_still_high():
    assert _tier("read", "aurora", 60).tier == RiskTier.HIGH


@pytest.mark.parametrize(
    ("permission", "resource", "minutes", "reason"),
    [
        ("admin", "helios", 30, "production or administrator"),
        ("read", "prod-database", 30, "production or administrator"),
        ("write", "aurora", 9 * 60, "over the 480 min limit"),
        ("read", "helios", 25 * 60, "over the 1440 min limit"),
        ("delete", "helios", 30, "unknown permission"),
    ],
)
def test_forbidden_requests_are_denied_with_a_reason(permission, resource, minutes, reason):
    decision = _tier(permission, resource, minutes)
    assert decision.tier == RiskTier.DENY
    assert any(reason in item for item in decision.reasons)


@pytest.mark.parametrize("status", [EmploymentStatus.DEPARTING, EmploymentStatus.INACTIVE])
def test_orphaned_agents_cannot_get_access(status):
    decision = _tier("read", "helios", 30, sponsor=_sponsor(status))
    assert decision.tier == RiskTier.DENY
    assert "the agent has no active human sponsor" in decision.reasons


# Identity and service token


def test_only_the_hash_of_an_agent_key_is_used():
    assert hash_agent_key("secret-key") == hash_agent_key("secret-key")
    assert "secret-key" not in hash_agent_key("secret-key")
    assert len(hash_agent_key("secret-key")) == 64


def test_service_token_must_match_and_be_configured():
    check_service_token("tok", "tok")
    for provided, expected in [("bad", "tok"), (None, "tok"), ("tok", "")]:
        with pytest.raises(AgentAuthError):
            check_service_token(provided, expected)


def test_endpoints_refuse_callers_without_credentials():
    client = TestClient(app)
    assert client.get("/agent-identity").status_code == 401
    assert client.get("/access-grants/mine").status_code == 401
    assert client.post("/access-grants/expire-due").status_code == 401


# Temporary grants


def _grant(expires_at, status=ResourceState.ACTIVE, kind="temporary_grant"):
    return CompanyResource(
        id=uuid4(), person_id=uuid4(), resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key=f"credential:bot:grant:{uuid4().hex[:6]}", status=status,
        details_data={"kind": kind, "expires_at": expires_at.isoformat(), "agent_key": "agent:bot"},
        idempotency_key=str(uuid4()),
    )


def test_only_active_temporary_grants_past_expiry_are_due():
    past = _grant(NOW - timedelta(minutes=1))
    future = _grant(NOW + timedelta(hours=2))
    released = _grant(NOW - timedelta(minutes=1), status=ResourceState.REVOKED)
    standing = _grant(NOW - timedelta(minutes=1), kind="api_token")
    assert due_grants([past, future, released, standing], NOW) == [past]


def test_mock_company_creates_grants_as_active_resources():
    assert ActionType.GRANT_TEMPORARY in CREATION_ACTIONS
    assert target_resource_state(ActionType.GRANT_TEMPORARY, ResourceType.AGENT_CREDENTIAL) == ResourceState.ACTIVE


def test_grant_plan_passes_validation_for_an_access_request():
    case = Case(id=uuid4(), case_type=CaseType.ACCESS_REQUEST, subject_person_id=uuid4(), case_facts={})
    context = CasePolicyContextResponse(
        case_id=case.id, search_query="q",
        evidence=[PolicyEvidenceResponse(evidence_id="POL-AGENT-V1-C0", policy_code="AGENT",
                                         version_number=1, text="rules", score=1.0)],
    )
    plan = GeneratedCasePlan(summary="Grant write on aurora for two hours.", actions=[PlannedAction(
        sequence=1, action_type=ActionType.GRANT_TEMPORARY, resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key="credential:aurora-release-bot:grant:1a2b3c4d",
        requested_data={"permission": "write", "expires_at": NOW.isoformat()},
        reason="Release v2.4 needs a tag.", evidence_ids=["POL-AGENT-V1-C0"],
    )], warnings=[])
    validate_generated_plan(plan, case=case, policy_context=context, resources=[])
