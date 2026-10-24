from __future__ import annotations

from uuid import uuid4

import pytest

from app.enums import ActionType, ResourceState, ResourceType
from app.mock_company.service import (
    APPLIED_KEYS_FIELD,
    IdempotencyConflictError,
    has_applied_key,
    is_mutation_replay,
)
from app.models import CompanyResource
from app.schemas import MockResourceApplyRequest


CREATION_KEY = "seed:arif:github-aurora-write"
REVOKE_KEY = "case:offboarding:revoke-github"


def _resource(applied_keys: dict | None = None) -> CompanyResource:
    details = {}
    if applied_keys is not None:
        details[APPLIED_KEYS_FIELD] = applied_keys
    return CompanyResource(
        resource_type=ResourceType.GITHUB_ACCESS,
        status=ResourceState.ACTIVE,
        resource_key="github:aurora:arif",
        details_data=details,
        idempotency_key=CREATION_KEY,
    )


def _request(
    idempotency_key: str = REVOKE_KEY,
    action_type: ActionType = ActionType.REVOKE,
    resource_type: ResourceType = ResourceType.GITHUB_ACCESS,
) -> MockResourceApplyRequest:
    return MockResourceApplyRequest(
        action_id=uuid4(),
        person_id=uuid4(),
        action_type=action_type,
        resource_type=resource_type,
        resource_key="github:aurora:arif",
        idempotency_key=idempotency_key,
    )


def test_first_mutation_is_not_a_replay():
    resource = _resource()

    assert is_mutation_replay(resource, None, _request()) is False


def test_recorded_mutation_key_is_a_replay():
    resource = _resource({REVOKE_KEY: ActionType.REVOKE.value})

    assert is_mutation_replay(resource, None, _request()) is True


def test_recorded_key_with_different_action_conflicts():
    resource = _resource({REVOKE_KEY: ActionType.REVOKE.value})
    request = _request(action_type=ActionType.DISABLE)

    with pytest.raises(IdempotencyConflictError):
        is_mutation_replay(resource, None, request)


def test_key_held_by_another_resource_conflicts():
    resource = _resource()
    other = _resource()

    with pytest.raises(IdempotencyConflictError):
        is_mutation_replay(resource, other, _request())


def test_key_held_when_target_resource_is_missing_conflicts():
    with pytest.raises(IdempotencyConflictError):
        is_mutation_replay(None, _resource(), _request())


def test_missing_resource_without_key_holder_is_not_a_replay():
    assert is_mutation_replay(None, None, _request()) is False


def test_legacy_row_with_overwritten_key_is_a_replay():
    resource = _resource()
    resource.idempotency_key = REVOKE_KEY

    assert is_mutation_replay(resource, resource, _request()) is True


def test_legacy_row_with_wrong_resource_type_conflicts():
    resource = _resource()
    resource.idempotency_key = REVOKE_KEY
    request = _request(resource_type=ResourceType.EMAIL_ACCOUNT)

    with pytest.raises(IdempotencyConflictError):
        is_mutation_replay(resource, resource, request)


def test_creation_key_stays_valid_after_mutation():
    resource = _resource({REVOKE_KEY: ActionType.REVOKE.value})

    assert has_applied_key(resource, CREATION_KEY, ActionType.ASSIGN)
    assert has_applied_key(resource, REVOKE_KEY, ActionType.REVOKE)
    assert not has_applied_key(resource, REVOKE_KEY, ActionType.DISABLE)
    assert not has_applied_key(resource, "unknown-key", ActionType.REVOKE)
