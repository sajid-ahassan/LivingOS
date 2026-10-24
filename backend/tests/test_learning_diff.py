from __future__ import annotations

from app.learning.service import _structured_revision_diff
from app.models import CasePlan


def _ai_offboarding_plan() -> CasePlan:
    return CasePlan(plan_data={
        "summary": "AI plan",
        "revocations": [{"action_type": "REVOKE", "resource_type": "GITHUB_ACCESS",
                         "resource_key": "github:aurora:arif", "requested_data": {}}],
        "asset_returns": [],
        "reassignments": [{"action_type": "REASSIGN", "resource_type": "AGENT_CREDENTIAL",
                           "resource_key": "credential:aurora-release-bot",
                           "requested_data": {"successor_person_id": "nabil"}}],
    })


def _manager_revision() -> CasePlan:
    return CasePlan(plan_data={
        "summary": "Revision",
        "actions": [
            {"action_type": "REVOKE", "resource_type": "GITHUB_ACCESS",
             "resource_key": "github:aurora:arif", "requested_data": {}},
            {"action_type": "DOWNSCOPE", "resource_type": "AGENT_CREDENTIAL",
             "resource_key": "credential:aurora-release-bot",
             "requested_data": {"successor_person_id": "nabil", "permission": "read"}},
        ],
    })


def test_offboarding_correction_is_one_changed_step():
    diff = _structured_revision_diff(_ai_offboarding_plan(), _manager_revision())
    assert diff["added"] == [] and diff["removed"] == []
    [change] = diff["changed"]
    assert change["before"]["action_type"] == "REASSIGN"
    assert change["after"]["action_type"] == "DOWNSCOPE"
    assert change["after"]["requested_data"]["permission"] == "read"


def test_identical_plans_have_no_diff():
    plan = _manager_revision()
    assert _structured_revision_diff(plan, plan) == {"added": [], "removed": [], "changed": []}
