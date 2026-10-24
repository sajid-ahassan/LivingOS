"""Resource state and owner after an action, shared by the mock company
adapter (which applies actions) and execution verification (which checks
them), so the two can never disagree."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.enums import ActionType, ResourceState, ResourceType


ACTION_STATE_MAP = {
    ActionType.CREATE: ResourceState.ACTIVE,
    ActionType.ASSIGN: ResourceState.ASSIGNED,
    ActionType.DISABLE: ResourceState.DISABLED,
    ActionType.REVOKE: ResourceState.REVOKED,
    ActionType.REASSIGN: ResourceState.REASSIGNED,
    ActionType.REQUEST_RETURN: ResourceState.RETURN_REQUESTED,
    ActionType.DOWNSCOPE: ResourceState.ACTIVE,
}


# A reassigned agent keeps running under its new sponsor, unlike a
# reassigned work item, which is finished for the previous owner.
AGENT_RESOURCE_TYPES = {
    ResourceType.AI_AGENT,
    ResourceType.AGENT_CREDENTIAL,
}


def target_resource_state(
    action_type: ActionType,
    resource_type: ResourceType | None = None,
) -> ResourceState:
    if (
        action_type == ActionType.REASSIGN
        and resource_type in AGENT_RESOURCE_TYPES
    ):
        return ResourceState.ACTIVE
    try:
        return ACTION_STATE_MAP[action_type]
    except KeyError as error:
        raise ValueError(
            f"Unsupported resource action: {action_type}"
        ) from error


def successor_from_parameters(parameters: dict[str, Any]) -> UUID | None:
    value = (parameters or {}).get("successor_person_id")
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def action_moves_owner(
    action_type: ActionType,
    parameters: dict[str, Any],
) -> bool:
    """REASSIGN always moves the owner; DOWNSCOPE does when a successor is named
    (offboarding hands the credential over and lowers it in one step)."""
    if action_type == ActionType.REASSIGN:
        return True
    # Presence, not validity: a malformed successor must fail loudly later
    # rather than silently leave the credential with the old owner.
    return action_type == ActionType.DOWNSCOPE and bool(
        (parameters or {}).get("successor_person_id")
    )
