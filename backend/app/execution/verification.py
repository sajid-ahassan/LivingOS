from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.enums import (
    ActionState,
    ActionType,
    AuditActorType,
    CaseState,
    ResourceState,
)
from app.models import Case, CaseAction, CompanyResource


EXPECTED_RESOURCE_STATES = {
    ActionType.CREATE: ResourceState.ACTIVE,
    ActionType.ASSIGN: ResourceState.ASSIGNED,
    ActionType.DISABLE: ResourceState.DISABLED,
    ActionType.REVOKE: ResourceState.REVOKED,
    ActionType.REASSIGN: ResourceState.REASSIGNED,
    ActionType.REQUEST_RETURN: ResourceState.RETURN_REQUESTED,
}


class ActionVerificationError(ValueError):
    pass


def _resource_key(action: CaseAction) -> str:
    value = (action.requested_data or {}).get("resource_key")

    if not isinstance(value, str) or not value.strip():
        raise ActionVerificationError(
            f"Action {action.id} has no valid resource_key."
        )

    return value.strip()


def _expected_person_id(
    action: CaseAction,
    case: Case,
) -> UUID:
    if action.action_type != ActionType.REASSIGN:
        return case.subject_person_id

    parameters = (action.requested_data or {}).get("parameters", {})
    successor_value = parameters.get("successor_person_id")

    try:
        return UUID(str(successor_value))
    except (TypeError, ValueError) as error:
        raise ActionVerificationError(
            "REASSIGN has no valid successor_person_id."
        ) from error


def _validate_resource(
    resource: CompanyResource,
    action: CaseAction,
    case: Case,
) -> None:
    mismatches: list[str] = []
    expected_state = EXPECTED_RESOURCE_STATES[action.action_type]

    if resource.resource_type != action.resource_type:
        mismatches.append("resource_type")

    if resource.person_id != _expected_person_id(action, case):
        mismatches.append("person_id")

    if resource.status != expected_state:
        mismatches.append("status")

    if resource.idempotency_key != action.idempotency_key:
        mismatches.append("idempotency_key")

    if resource.source_action_id != action.id:
        mismatches.append("source_action_id")

    if mismatches:
        raise ActionVerificationError(
            "Resource verification failed for fields: "
            + ", ".join(mismatches)
        )


def verify_action_result(
    db: Session,
    action: CaseAction,
    case: Case,
) -> CaseAction:
    if action.status != ActionState.SUCCEEDED:
        raise ActionVerificationError(
            f"Action {action.id} cannot be verified from "
            f"{action.status.value} state."
        )

    resource_key = _resource_key(action)
    resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == resource_key
        )
    )

    try:
        if resource is None:
            raise ActionVerificationError(
                f"Expected resource does not exist: {resource_key}"
            )

        _validate_resource(resource, action, case)

    except ActionVerificationError as error:
        action.status = ActionState.FAILED
        action.error_message = str(error)
        case.status = CaseState.FAILED
        case.failure_reason = str(error)

        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_VERIFICATION_FAILED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={"status": ActionState.SUCCEEDED.value},
            after_data={
                "status": action.status.value,
                "error": str(error),
            },
            evidence_data={"resource_key": resource_key},
            correlation_id=case.id,
        )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        raise

    previous_result = dict(action.result_data or {})
    previous_result["verified"] = True
    previous_result["verified_resource_id"] = str(resource.id)

    action.status = ActionState.VERIFIED
    action.result_data = previous_result
    action.error_message = None

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_VERIFIED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={"status": ActionState.SUCCEEDED.value},
            after_data={
                "status": action.status.value,
                "resource_id": str(resource.id),
            },
            evidence_data={
                "resource_key": resource.resource_key,
                "resource_status": resource.status.value,
                "idempotency_key": action.idempotency_key,
            },
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return action
