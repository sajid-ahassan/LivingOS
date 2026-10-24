from collections.abc import Callable
from uuid import UUID

from app.cases.schemas import CasePolicyContextResponse
from app.enums import ActionType, CaseType, ResourceState, ResourceType
from app.models import Case, CompanyResource, Person
from app.offboarding.rules import (
    allowed_offboarding_actions,
    validate_access_evidence,
    validate_agent_coverage,
)
from app.planning.schemas import GeneratedCasePlan


ALLOWED_ACTIONS = {
    CaseType.ONBOARDING: {
        ActionType.CREATE,
        ActionType.ASSIGN,
    },
    CaseType.OFFBOARDING: {
        ActionType.DISABLE,
        ActionType.REVOKE,
        ActionType.REASSIGN,
        ActionType.REQUEST_RETURN,
        ActionType.DOWNSCOPE,
    },
    # Agent access changes: MCP grants (W5) and Guardian remediation.
    CaseType.ACCESS_REQUEST: {
        ActionType.GRANT_TEMPORARY,
        ActionType.DOWNSCOPE,
        ActionType.REVOKE,
    },
}


ALLOWED_RESOURCE_TYPES = {
    ActionType.CREATE: {
        ResourceType.EMAIL_ACCOUNT,
    },
    ActionType.ASSIGN: {
        ResourceType.GITHUB_ACCESS,
        ResourceType.LAPTOP,
        ResourceType.TRAINING,
    },
    ActionType.DISABLE: {
        ResourceType.EMAIL_ACCOUNT,
    },
    ActionType.REVOKE: {
        ResourceType.GITHUB_ACCESS,
        ResourceType.AI_AGENT,
        ResourceType.AGENT_CREDENTIAL,
    },
    ActionType.REASSIGN: {
        ResourceType.WORK_ITEM,
        ResourceType.KNOWLEDGE_DOCUMENT,
        ResourceType.AI_AGENT,
        ResourceType.AGENT_CREDENTIAL,
    },
    ActionType.REQUEST_RETURN: {
        ResourceType.LAPTOP,
    },
    ActionType.DOWNSCOPE: {
        ResourceType.AGENT_CREDENTIAL,
        ResourceType.GITHUB_ACCESS,
    },
    ActionType.GRANT_TEMPORARY: {
        ResourceType.AGENT_CREDENTIAL,
        ResourceType.GITHUB_ACCESS,
    },
}


MUTATION_ACTIONS = {
    ActionType.DISABLE,
    ActionType.REVOKE,
    ActionType.REASSIGN,
    ActionType.REQUEST_RETURN,
    ActionType.DOWNSCOPE,
}


ONBOARDING_REQUIREMENT_FIELDS = {
    ResourceType.EMAIL_ACCOUNT: "requires_email",
    ResourceType.GITHUB_ACCESS: "requires_github",
    ResourceType.LAPTOP: "requires_laptop",
    ResourceType.TRAINING: "requires_training",
}


SATISFYING_RESOURCE_STATES = {
    ResourceState.ACTIVE,
    ResourceState.ASSIGNED,
}


class GeneratedPlanValidationError(ValueError):
    pass


def validate_generated_plan(
    plan: GeneratedCasePlan,
    *,
    case: Case,
    policy_context: CasePolicyContextResponse,
    resources: list[CompanyResource],
    get_person: Callable[[UUID], Person | None] | None = None,
) -> None:
    errors: list[str] = []

    actual_sequence = [
        action.sequence
        for action in plan.actions
    ]
    expected_sequence = list(
        range(1, len(plan.actions) + 1)
    )

    if actual_sequence != expected_sequence:
        errors.append(
            "Action sequence must start at 1 and be consecutive."
        )

    allowed_evidence_ids = {
        item.evidence_id
        for item in policy_context.evidence
    }

    resources_by_key = {
        resource.resource_key: resource
        for resource in resources
    }

    seen_actions: set[tuple[str, str, str]] = set()
    seen_resource_keys: set[str] = set()

    for action in plan.actions:
        signature = (
            action.action_type.value,
            action.resource_type.value,
            action.resource_key,
        )

        if signature in seen_actions:
            errors.append(
                f"Duplicate action at sequence {action.sequence}."
            )

        seen_actions.add(signature)

        if action.resource_key in seen_resource_keys:
            errors.append(
                f"Resource key is repeated at sequence {action.sequence}."
            )

        seen_resource_keys.add(action.resource_key)

        if action.action_type not in ALLOWED_ACTIONS[case.case_type]:
            errors.append(
                f"{action.action_type.value} is not allowed "
                f"for {case.case_type.value}."
            )

        if action.resource_type not in ALLOWED_RESOURCE_TYPES[
            action.action_type
        ]:
            errors.append(
                f"{action.action_type.value} cannot be used with "
                f"{action.resource_type.value}."
            )

        invalid_evidence = set(action.evidence_ids).difference(
            allowed_evidence_ids
        )

        if invalid_evidence:
            errors.append(
                f"Action {action.sequence} cites unavailable evidence: "
                f"{sorted(invalid_evidence)}."
            )

        existing_resource = resources_by_key.get(
            action.resource_key
        )

        if action.action_type in MUTATION_ACTIONS:
            if existing_resource is None:
                errors.append(
                    f"Action {action.sequence} targets an "
                    "unknown resource key."
                )
            elif (
                existing_resource.resource_type
                != action.resource_type
            ):
                errors.append(
                    f"Action {action.sequence} has the wrong "
                    "resource type for its resource key."
                )
            elif case.case_type == CaseType.OFFBOARDING:
                allowed = allowed_offboarding_actions(existing_resource)
                if allowed and action.action_type not in allowed:
                    errors.append(
                        f"Action {action.sequence} must be one of "
                        f"{sorted(item.value for item in allowed)} "
                        f"for {action.resource_key}."
                    )

        elif existing_resource is not None:
            errors.append(
                f"Action {action.sequence} would duplicate an "
                "existing resource."
            )

        if case.case_type == CaseType.ONBOARDING:
            requirement_field = ONBOARDING_REQUIREMENT_FIELDS.get(
                action.resource_type
            )

            if (
                requirement_field is None
                or (case.case_facts or {}).get(requirement_field) is not True
            ):
                errors.append(
                    f"Action {action.sequence} is not explicitly "
                    "required by the onboarding case facts."
                )

            if any(
                resource.resource_type == action.resource_type
                and resource.status in SATISFYING_RESOURCE_STATES
                for resource in resources
            ):
                errors.append(
                    f"Action {action.sequence} duplicates an already "
                    "satisfied resource requirement."
                )

        if (
            action.action_type == ActionType.REASSIGN
            and not action.requested_data.get("successor_person_id")
        ):
            errors.append(
                f"Action {action.sequence} requires successor_person_id."
            )

        if (
            action.action_type == ActionType.REQUEST_RETURN
            and not action.requested_data.get("due_date")
        ):
            errors.append(
                f"Action {action.sequence} requires due_date."
            )

    if case.case_type == CaseType.OFFBOARDING:
        errors.extend(
            validate_agent_coverage(
                plan.actions,
                resources,
                subject_person_id=case.subject_person_id,
                get_person=get_person,
            )
        )
        errors.extend(validate_access_evidence(plan.actions, policy_context))

    if errors:
        raise GeneratedPlanValidationError(
            " ".join(errors)
        )
