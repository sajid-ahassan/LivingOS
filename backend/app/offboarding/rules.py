from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING
from uuid import UUID

from app.enums import ActionType, EmploymentStatus, ResourceState, ResourceType
from app.models import CompanyResource, Person
from app.resource_rules import AGENT_RESOURCE_TYPES

if TYPE_CHECKING:
    from app.cases.schemas import CasePolicyContextResponse
    from app.planning.schemas import PlannedAction


TERMINAL_RESOURCE_STATES = {
    ResourceState.DISABLED,
    ResourceState.REVOKED,
    ResourceState.RETURN_REQUESTED,
    ResourceState.RETURNED,
    ResourceState.REASSIGNED,
    ResourceState.EXPIRED,
}


# Agents can be handed to a successor or shut down; the planner proposes
# which, a manager may change it, and these rules decide what is valid.
AGENT_OFFBOARDING_ACTIONS = {
    ResourceType.AI_AGENT: frozenset({
        ActionType.REASSIGN,
        ActionType.REVOKE,
    }),
    ResourceType.AGENT_CREDENTIAL: frozenset({
        ActionType.REASSIGN,
        ActionType.DOWNSCOPE,
        ActionType.REVOKE,
    }),
}


AGENT_ACTIVE_STATES = {
    ResourceState.ACTIVE,
    ResourceState.ASSIGNED,
    ResourceState.SUSPENDED,
}


# Credential actions that keep the agent running under the successor.
HANDOVER_CREDENTIAL_ACTIONS = {
    ActionType.REASSIGN,
    ActionType.DOWNSCOPE,
}


ACCESS_POLICY_CODE = "ACCESS"
AGENT_POLICY_CODE = "AGENT"


# Approved agent metadata the planner may see; never key hashes or secrets.
AGENT_METADATA_FIELDS = ("agent_name", "purpose", "scopes", "credential_key")


def safe_resource_metadata(resource: CompanyResource) -> dict:
    details = resource.details_data or {}
    metadata = {
        "resource_type": resource.resource_type.value,
        "resource_key": resource.resource_key,
        "status": resource.status.value,
        "owner_id": str(resource.person_id),
        "title": details.get("title"),
        "due_date": details.get("due_date"),
    }
    if resource.resource_type == ResourceType.AI_AGENT:
        for field in AGENT_METADATA_FIELDS:
            metadata[field] = details.get(field)
    return metadata


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


def allowed_offboarding_actions(resource: CompanyResource) -> frozenset[ActionType]:
    if resource.resource_type in AGENT_RESOURCE_TYPES:
        if resource.status in AGENT_ACTIVE_STATES:
            return AGENT_OFFBOARDING_ACTIONS[resource.resource_type]
        return frozenset()

    required_action = required_action_for_resource(resource)
    return frozenset({required_action}) if required_action else frozenset()


def _successor_id(action: PlannedAction) -> UUID | None:
    value = action.requested_data.get("successor_person_id")
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _successor_errors(
    action: PlannedAction,
    subject_person_id: UUID,
    get_person: Callable[[UUID], Person | None] | None,
) -> list[str]:
    successor_id = _successor_id(action)
    if successor_id is None:
        return [
            f"{action.action_type.value} for {action.resource_key} requires "
            "a valid successor_person_id."
        ]
    if successor_id == subject_person_id:
        return [f"The departing sponsor cannot keep {action.resource_key}."]
    if get_person is None:
        return []
    successor = get_person(successor_id)
    if successor is None:
        return [f"Successor does not exist for {action.resource_key}."]
    if successor.employment_status != EmploymentStatus.ACTIVE:
        return [
            f"Successor for {action.resource_key} must be ACTIVE, "
            f"not {successor.employment_status.value}."
        ]
    return []


def validate_agent_coverage(
    actions: Iterable[PlannedAction],
    resources: Iterable[CompanyResource],
    *,
    subject_person_id: UUID,
    get_person: Callable[[UUID], Person | None] | None = None,
) -> list[str]:
    """No agent or agent credential may stay with a departing sponsor."""
    errors: list[str] = []
    planned: dict[str, list[PlannedAction]] = {}
    for action in actions:
        planned.setdefault(action.resource_key, []).append(action)

    agent_resources = [
        resource
        for resource in resources
        if allowed_offboarding_actions(resource)
        and resource.resource_type in AGENT_RESOURCE_TYPES
    ]
    by_key = {resource.resource_key: resource for resource in agent_resources}

    chosen: dict[str, PlannedAction] = {}
    for resource in agent_resources:
        matching = planned.get(resource.resource_key, [])
        if len(matching) != 1:
            errors.append(
                f"{resource.resource_type.value} {resource.resource_key} needs "
                "exactly one offboarding action: "
                + " or ".join(
                    sorted(a.value for a in allowed_offboarding_actions(resource))
                )
                + "."
            )
            continue
        action = matching[0]
        if action.action_type not in allowed_offboarding_actions(resource):
            errors.append(
                f"{action.action_type.value} is not a valid offboarding action "
                f"for {resource.resource_type.value} {resource.resource_key}."
            )
            continue
        chosen[resource.resource_key] = action
        # In offboarding a DOWNSCOPE also moves the credential off the
        # departing sponsor, so it needs a successor just like REASSIGN.
        if action.action_type in HANDOVER_CREDENTIAL_ACTIONS:
            errors.extend(
                _successor_errors(action, subject_person_id, get_person)
            )

    for agent in agent_resources:
        if agent.resource_type != ResourceType.AI_AGENT:
            continue
        agent_action = chosen.get(agent.resource_key)
        credential_key = (agent.details_data or {}).get("credential_key")
        credential_action = chosen.get(credential_key) if credential_key else None
        if agent_action is None or credential_key not in by_key:
            continue
        if credential_action is None:
            continue

        if agent_action.action_type == ActionType.REVOKE:
            if credential_action.action_type != ActionType.REVOKE:
                errors.append(
                    f"Agent {agent.resource_key} is revoked, so credential "
                    f"{credential_key} must be revoked too."
                )
        elif credential_action.action_type not in HANDOVER_CREDENTIAL_ACTIONS:
            errors.append(
                f"Agent {agent.resource_key} is reassigned, so credential "
                f"{credential_key} must be REASSIGN or DOWNSCOPE."
            )
        elif _successor_id(credential_action) != _successor_id(agent_action):
            errors.append(
                f"Credential {credential_key} must move to the same successor "
                f"as agent {agent.resource_key}."
            )

    return errors


def validate_access_evidence(
    actions: Iterable[PlannedAction],
    policy_context: CasePolicyContextResponse,
) -> list[str]:
    """Agent steps must cite ACCESS (and AGENT, when retrieved) evidence.

    Guardian finds dependent plans through these citations, so an agent step
    without ACCESS evidence would be invisible when the Access Policy changes.
    """
    code_by_evidence = {
        item.evidence_id: item.policy_code for item in policy_context.evidence
    }
    retrieved_codes = set(code_by_evidence.values())
    errors: list[str] = []

    for action in actions:
        if action.resource_type not in AGENT_RESOURCE_TYPES:
            continue
        cited_codes = {
            code_by_evidence[evidence_id]
            for evidence_id in action.evidence_ids
            if evidence_id in code_by_evidence
        }
        if ACCESS_POLICY_CODE not in retrieved_codes:
            errors.append(
                f"No {ACCESS_POLICY_CODE} policy evidence was retrieved, so "
                f"agent step {action.resource_key} cannot be justified."
            )
        elif ACCESS_POLICY_CODE not in cited_codes:
            errors.append(
                f"Agent step {action.resource_key} must cite "
                f"{ACCESS_POLICY_CODE} policy evidence."
            )
        if (
            AGENT_POLICY_CODE in retrieved_codes
            and AGENT_POLICY_CODE not in cited_codes
        ):
            errors.append(
                f"Agent step {action.resource_key} must cite "
                f"{AGENT_POLICY_CODE} policy evidence."
            )

    return errors


def agent_evidence_instruction(
    resources: Iterable[CompanyResource],
    policy_context: CasePolicyContextResponse,
) -> str:
    """Name, from the retrieved evidence, the exact IDs agent steps must cite.

    Deterministic: the IDs come from retrieval, not from the model, so the
    planner cannot drop the ACCESS link that Policy Guardian depends on.
    """
    if not any(resource.resource_type in AGENT_RESOURCE_TYPES for resource in resources):
        return ""
    required = [
        item.evidence_id
        for code in (ACCESS_POLICY_CODE, AGENT_POLICY_CODE)
        for item in policy_context.evidence
        if item.policy_code == code
    ]
    if not required:
        return ""
    return (
        "\n\nREQUIRED CITATIONS: every AI_AGENT and AGENT_CREDENTIAL action must "
        "include all of these evidence IDs in evidence_ids: " + ", ".join(required)
    )


def derive_agent_credential_actions(plan, resources: Iterable[CompanyResource]):
    """Make each agent's credential follow the planner's decision for the agent.

    The planner decides an agent's fate (REASSIGN or REVOKE); what happens to
    its credential follows from that by rule, not judgment: REVOKE with
    REVOKE, REASSIGN with a REASSIGN (key rotation) to the same successor. Any
    credential action the model wrote for a linked credential is replaced.
    A manager can still choose DOWNSCOPE in a revision. Returns a new plan.
    """
    from app.planning.schemas import PlannedAction

    resources = list(resources)
    by_key = {resource.resource_key: resource for resource in resources}
    agent_credentials = {
        resource.resource_key: (resource.details_data or {}).get("credential_key")
        for resource in resources
        if resource.resource_type == ResourceType.AI_AGENT
        and allowed_offboarding_actions(resource)
    }
    linked = {
        key
        for key in agent_credentials.values()
        if key in by_key and allowed_offboarding_actions(by_key[key])
    }

    def keep(action) -> bool:
        return action.resource_key not in linked

    revocations = [a for a in plan.revocations if keep(a)]
    reassignments = [a for a in plan.reassignments if keep(a)]

    for agent_action in [*plan.revocations, *plan.reassignments]:
        credential_key = agent_credentials.get(agent_action.resource_key)
        if agent_action.resource_type != ResourceType.AI_AGENT or credential_key not in linked:
            continue
        if agent_action.action_type == ActionType.REVOKE:
            derived = PlannedAction(
                sequence=agent_action.sequence,
                action_type=ActionType.REVOKE,
                resource_type=ResourceType.AGENT_CREDENTIAL,
                resource_key=credential_key,
                requested_data={},
                reason=f"Credential is revoked with its agent {agent_action.resource_key}.",
                evidence_ids=list(agent_action.evidence_ids),
            )
            revocations.append(derived)
        elif agent_action.action_type == ActionType.REASSIGN:
            derived = PlannedAction(
                sequence=agent_action.sequence,
                action_type=ActionType.REASSIGN,
                resource_type=ResourceType.AGENT_CREDENTIAL,
                resource_key=credential_key,
                requested_data={
                    "successor_person_id": agent_action.requested_data.get(
                        "successor_person_id"
                    )
                },
                reason=(
                    f"Credential moves with its agent {agent_action.resource_key}; "
                    "the key is rotated for the new sponsor."
                ),
                evidence_ids=list(agent_action.evidence_ids),
            )
            reassignments.append(derived)

    return plan.model_copy(
        update={"revocations": revocations, "reassignments": reassignments}
    )
