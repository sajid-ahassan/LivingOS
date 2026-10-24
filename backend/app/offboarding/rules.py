from __future__ import annotations

from app.enums import ActionType, ResourceState, ResourceType
from app.models import CompanyResource


TERMINAL_RESOURCE_STATES = {
    ResourceState.DISABLED,
    ResourceState.REVOKED,
    ResourceState.RETURN_REQUESTED,
    ResourceState.RETURNED,
    ResourceState.REASSIGNED,
}


def safe_resource_metadata(resource: CompanyResource) -> dict:
    details = resource.details_data or {}
    return {
        "resource_type": resource.resource_type.value,
        "resource_key": resource.resource_key,
        "status": resource.status.value,
        "owner_id": str(resource.person_id),
        "title": details.get("title"),
        "due_date": details.get("due_date"),
    }


def required_action_for_resource(resource: CompanyResource) -> ActionType | None:
    if resource.status in TERMINAL_RESOURCE_STATES:
        return None

    if (
        resource.resource_type == ResourceType.EMAIL_ACCOUNT
        and resource.status == ResourceState.ACTIVE
    ):
        return ActionType.DISABLE

    if (
        resource.resource_type == ResourceType.GITHUB_ACCESS
        and resource.status in {ResourceState.ACTIVE, ResourceState.ASSIGNED}
    ):
        return ActionType.REVOKE

    if (
        resource.resource_type == ResourceType.LAPTOP
        and resource.status == ResourceState.ASSIGNED
    ):
        return ActionType.REQUEST_RETURN

    if (
        resource.resource_type == ResourceType.WORK_ITEM
        and resource.status == ResourceState.OPEN
    ):
        return ActionType.REASSIGN

    if (
        resource.resource_type == ResourceType.KNOWLEDGE_DOCUMENT
        and resource.status in {
            ResourceState.ACTIVE,
            ResourceState.OPEN,
            ResourceState.ASSIGNED,
        }
    ):
        return ActionType.REASSIGN

    return None
