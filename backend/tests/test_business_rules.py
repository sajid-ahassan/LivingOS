from __future__ import annotations

import pytest

from app.enums import (
    ActionType,
    CaseType,
    ResourceState,
    ResourceType,
)
from app.models import CompanyResource
from app.offboarding.service import _required_action_for_resource
from app.planning.validation import (
    ALLOWED_ACTIONS,
    ALLOWED_RESOURCE_TYPES,
    MUTATION_ACTIONS,
    ONBOARDING_REQUIREMENT_FIELDS,
    SATISFYING_RESOURCE_STATES,
)


def _resource(
    resource_type: ResourceType,
    status: ResourceState,
) -> CompanyResource:
    return CompanyResource(
        resource_type=resource_type,
        status=status,
        resource_key=f"test:{resource_type.value}:{status.value}",
        details_data={},
        idempotency_key=f"test:{resource_type.value}:{status.value}",
    )


def test_onboarding_allows_only_creation_actions():
    assert ALLOWED_ACTIONS[CaseType.ONBOARDING] == {
        ActionType.CREATE,
        ActionType.ASSIGN,
    }

    assert ActionType.DISABLE not in ALLOWED_ACTIONS[CaseType.ONBOARDING]
    assert ActionType.REVOKE not in ALLOWED_ACTIONS[CaseType.ONBOARDING]
    assert ActionType.REASSIGN not in ALLOWED_ACTIONS[CaseType.ONBOARDING]
    assert (
        ActionType.REQUEST_RETURN
        not in ALLOWED_ACTIONS[CaseType.ONBOARDING]
    )


def test_offboarding_allows_only_mutation_actions():
    assert ALLOWED_ACTIONS[CaseType.OFFBOARDING] == {
        ActionType.DISABLE,
        ActionType.REVOKE,
        ActionType.REASSIGN,
        ActionType.REQUEST_RETURN,
    }

    assert ActionType.CREATE not in ALLOWED_ACTIONS[CaseType.OFFBOARDING]
    assert ActionType.ASSIGN not in ALLOWED_ACTIONS[CaseType.OFFBOARDING]


@pytest.mark.parametrize(
    ("action_type", "allowed_resource_types"),
    [
        (
            ActionType.CREATE,
            {ResourceType.EMAIL_ACCOUNT},
        ),
        (
            ActionType.ASSIGN,
            {
                ResourceType.GITHUB_ACCESS,
                ResourceType.LAPTOP,
                ResourceType.TRAINING,
            },
        ),
        (
            ActionType.DISABLE,
            {ResourceType.EMAIL_ACCOUNT},
        ),
        (
            ActionType.REVOKE,
            {ResourceType.GITHUB_ACCESS},
        ),
        (
            ActionType.REASSIGN,
            {
                ResourceType.WORK_ITEM,
                ResourceType.KNOWLEDGE_DOCUMENT,
            },
        ),
        (
            ActionType.REQUEST_RETURN,
            {ResourceType.LAPTOP},
        ),
    ],
)
def test_action_resource_allowlist(
    action_type,
    allowed_resource_types,
):
    assert ALLOWED_RESOURCE_TYPES[action_type] == allowed_resource_types


def test_mutation_action_set_is_complete():
    assert MUTATION_ACTIONS == {
        ActionType.DISABLE,
        ActionType.REVOKE,
        ActionType.REASSIGN,
        ActionType.REQUEST_RETURN,
    }


def test_onboarding_requirement_mapping_is_complete():
    assert ONBOARDING_REQUIREMENT_FIELDS == {
        ResourceType.EMAIL_ACCOUNT: "requires_email",
        ResourceType.GITHUB_ACCESS: "requires_github",
        ResourceType.LAPTOP: "requires_laptop",
        ResourceType.TRAINING: "requires_training",
    }


def test_only_active_or_assigned_resources_satisfy_onboarding_requirement():
    assert SATISFYING_RESOURCE_STATES == {
        ResourceState.ACTIVE,
        ResourceState.ASSIGNED,
    }


@pytest.mark.parametrize(
    ("resource_type", "resource_state", "expected_action"),
    [
        (
            ResourceType.EMAIL_ACCOUNT,
            ResourceState.ACTIVE,
            ActionType.DISABLE,
        ),
        (
            ResourceType.GITHUB_ACCESS,
            ResourceState.ACTIVE,
            ActionType.REVOKE,
        ),
        (
            ResourceType.GITHUB_ACCESS,
            ResourceState.ASSIGNED,
            ActionType.REVOKE,
        ),
        (
            ResourceType.LAPTOP,
            ResourceState.ASSIGNED,
            ActionType.REQUEST_RETURN,
        ),
        (
            ResourceType.WORK_ITEM,
            ResourceState.OPEN,
            ActionType.REASSIGN,
        ),
        (
            ResourceType.KNOWLEDGE_DOCUMENT,
            ResourceState.ACTIVE,
            ActionType.REASSIGN,
        ),
        (
            ResourceType.KNOWLEDGE_DOCUMENT,
            ResourceState.OPEN,
            ActionType.REASSIGN,
        ),
        (
            ResourceType.KNOWLEDGE_DOCUMENT,
            ResourceState.ASSIGNED,
            ActionType.REASSIGN,
        ),
    ],
)
def test_offboarding_resource_action_mapping(
    resource_type,
    resource_state,
    expected_action,
):
    resource = _resource(resource_type, resource_state)
    assert _required_action_for_resource(resource) == expected_action


@pytest.mark.parametrize(
    "terminal_state",
    [
        ResourceState.DISABLED,
        ResourceState.REVOKED,
        ResourceState.RETURN_REQUESTED,
        ResourceState.RETURNED,
        ResourceState.REASSIGNED,
    ],
)
def test_terminal_resources_do_not_generate_new_offboarding_actions(
    terminal_state,
):
    resource = _resource(
        ResourceType.EMAIL_ACCOUNT,
        terminal_state,
    )

    assert _required_action_for_resource(resource) is None


def test_unhandled_resource_state_does_not_invent_action():
    resource = _resource(
        ResourceType.LAPTOP,
        ResourceState.ACTIVE,
    )

    assert _required_action_for_resource(resource) is None
