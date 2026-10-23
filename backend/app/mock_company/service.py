from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.enums import (
    ActionType,
    AuditActorType,
    ResourceState,
    ResourceType,
)
from app.models import Case, CaseAction, CompanyResource, Person
from app.schemas import MockResourceApplyRequest

ACTION_STATE_MAP = {
    ActionType.CREATE: ResourceState.ACTIVE,
    ActionType.ASSIGN: ResourceState.ASSIGNED,
    ActionType.DISABLE: ResourceState.DISABLED,
    ActionType.REVOKE: ResourceState.REVOKED,
    ActionType.REASSIGN: ResourceState.REASSIGNED,
    ActionType.REQUEST_RETURN: ResourceState.RETURN_REQUESTED,
}


AUDIT_EVENT_TYPE_MAP = {
    ActionType.CREATE: "RESOURCE_CREATED",
    ActionType.ASSIGN: "RESOURCE_ASSIGNED",
    ActionType.DISABLE: "RESOURCE_DISABLED",
    ActionType.REVOKE: "RESOURCE_REVOKED",
    ActionType.REASSIGN: "RESOURCE_REASSIGNED",
    ActionType.REQUEST_RETURN: "RESOURCE_RETURN_REQUESTED",
}

CREATION_ACTIONS = {
    ActionType.CREATE,
    ActionType.ASSIGN,
}


MUTATION_ACTIONS = {
    ActionType.DISABLE,
    ActionType.REVOKE,
    ActionType.REASSIGN,
    ActionType.REQUEST_RETURN,
}


MUTATION_RESOURCE_TYPES = {
    ActionType.DISABLE: {
        ResourceType.EMAIL_ACCOUNT,
    },
    ActionType.REVOKE: {
        ResourceType.GITHUB_ACCESS,
    },
    ActionType.REASSIGN: {
        ResourceType.WORK_ITEM,
        ResourceType.KNOWLEDGE_DOCUMENT,
    },
    ActionType.REQUEST_RETURN: {
        ResourceType.LAPTOP,
    },
}


class ResourceNotFoundError(ValueError):
    pass


class ResourceConflictError(ValueError):
    pass


class IdempotencyConflictError(ValueError):
    pass


def get_target_resource_state(
    action_type: ActionType,
) -> ResourceState:
    try:
        return ACTION_STATE_MAP[action_type]
    except KeyError as error:
        raise ValueError(
            f"Unsupported resource action: {action_type}"
        ) from error


def validate_source_action(
    db: Session,
    request: MockResourceApplyRequest,
) -> CaseAction:
    source_action = db.get(CaseAction, request.action_id)

    if source_action is None:
        raise ResourceNotFoundError(
            f"Case action does not exist: {request.action_id}"
        )

    source_case = db.get(Case, source_action.case_id)

    if source_case is None:
        raise ResourceNotFoundError(
            f"Source case does not exist: {source_action.case_id}"
        )

    if request.case_id is not None and request.case_id != source_case.id:
        raise ResourceConflictError(
            "The supplied case does not match the source action."
        )

    if source_case.subject_person_id != request.person_id:
        raise ResourceConflictError(
            "The supplied person does not match the source case."
        )

    if (
        source_action.action_type != request.action_type
        or source_action.resource_type != request.resource_type
        or source_action.idempotency_key != request.idempotency_key
    ):
        raise ResourceConflictError(
            "The supplied operation does not match the source action."
        )

    return source_action



def create_or_assign_resource(
    db: Session,
    request: MockResourceApplyRequest,
) -> tuple[CompanyResource, bool]:
    if request.action_type not in CREATION_ACTIONS:
        raise ValueError(
            f"{request.action_type.value} is not a creation action."
        )

    person = db.get(Person, request.person_id)

    if person is None:
        raise ResourceNotFoundError(
            f"Person does not exist: {request.person_id}"
        )

    source_action = validate_source_action(db, request)

    replayed_resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.idempotency_key
            == request.idempotency_key
        )
    )

    if replayed_resource is not None:
        if (
            replayed_resource.resource_key
            != request.resource_key
            or replayed_resource.resource_type
            != request.resource_type
        ):
            raise IdempotencyConflictError(
                "The idempotency key was already used "
                "for a different resource request."
            )

        return replayed_resource, True

    existing_resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key
            == request.resource_key
        )
    )

    if existing_resource is not None:
        raise ResourceConflictError(
            f"Resource key already exists: "
            f"{request.resource_key}"
        )

    resource = CompanyResource(
        person_id=request.person_id,
        resource_type=request.resource_type,
        resource_key=request.resource_key,
        status=get_target_resource_state(
            request.action_type
        ),
        details_data=dict(request.requested_data),
        source_action_id=source_action.id,
        idempotency_key=request.idempotency_key,
    )

    db.add(resource)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.N8N,
            event_type=AUDIT_EVENT_TYPE_MAP[request.action_type],
            entity_type="company_resource",
            entity_id=resource.id,
            before_data=None,
            after_data=resource_audit_data(resource),
            evidence_data={
                "action_id": request.action_id,
                "requested_data": request.requested_data,
            },
            correlation_id=source_action.case_id,
        )

        db.commit()
        db.refresh(resource)

    except Exception:
        db.rollback()
        raise

    return resource, False






def mutate_resource(
    db: Session,
    request: MockResourceApplyRequest,
) -> tuple[CompanyResource, bool]:
    if request.action_type not in MUTATION_ACTIONS:
        raise ValueError(
            f"{request.action_type.value} is not "
            "a mutation action."
        )

    allowed_types = MUTATION_RESOURCE_TYPES[
        request.action_type
    ]

    if request.resource_type not in allowed_types:
        raise ValueError(
            f"{request.action_type.value} cannot be applied "
            f"to {request.resource_type.value}."
        )

    source_action = validate_source_action(db, request)

    replayed_resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.idempotency_key
            == request.idempotency_key
        )
    )

    if replayed_resource is not None:
        if (
            replayed_resource.resource_key
            != request.resource_key
            or replayed_resource.resource_type
            != request.resource_type
        ):
            raise IdempotencyConflictError(
                "The idempotency key was already used "
                "for a different resource request."
            )

        return replayed_resource, True

    resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key
            == request.resource_key
        )
    )

    if resource is None:
        raise ResourceNotFoundError(
            f"Resource does not exist: "
            f"{request.resource_key}"
        )

    if resource.resource_type != request.resource_type:
        raise ResourceConflictError(
            "The supplied resource type does not match "
            "the existing resource."
        )

    if resource.person_id != request.person_id:
        raise ResourceConflictError(
            "The resource does not belong to the "
            "supplied person."
        )
    before_data = resource_audit_data(resource)

    updated_details = dict(resource.details_data or {})
    updated_details.update(request.requested_data)

    if request.action_type == ActionType.REASSIGN:
        successor_value = request.requested_data.get(
            "successor_person_id"
        )

        if successor_value is None:
            raise ValueError(
                "REASSIGN requires successor_person_id."
            )

        try:
            successor_id = UUID(str(successor_value))
        except ValueError as error:
            raise ValueError(
                "successor_person_id must be a valid UUID."
            ) from error

        successor = db.get(Person, successor_id)

        if successor is None:
            raise ResourceNotFoundError(
                f"Successor does not exist: {successor_id}"
            )

        updated_details["previous_person_id"] = str(
            resource.person_id
        )
        resource.person_id = successor_id

    if request.action_type == ActionType.REQUEST_RETURN:
        if not request.requested_data.get("due_date"):
            raise ValueError(
                "REQUEST_RETURN requires due_date."
            )

    resource.status = get_target_resource_state(
        request.action_type
    )
    resource.details_data = updated_details
    resource.idempotency_key = request.idempotency_key

    resource.source_action_id = source_action.id

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.N8N,
            event_type=AUDIT_EVENT_TYPE_MAP[request.action_type],
            entity_type="company_resource",
            entity_id=resource.id,
            before_data=before_data,
            after_data=resource_audit_data(resource),
            evidence_data={
                "action_id": request.action_id,
                "requested_data": request.requested_data,
            },
            correlation_id=source_action.case_id,
        )

        db.commit()
        db.refresh(resource)

    except Exception:
        db.rollback()
        raise

    return resource, False





def apply_resource_action(
    db: Session,
    request: MockResourceApplyRequest,
) -> tuple[CompanyResource, bool]:
    if request.action_type in CREATION_ACTIONS:
        return create_or_assign_resource(
            db,
            request,
        )

    if request.action_type in MUTATION_ACTIONS:
        return mutate_resource(
            db,
            request,
        )

    raise ValueError(
        f"Unsupported action type: "
        f"{request.action_type.value}"
    )











def get_resource_by_key(
    db: Session,
    resource_key: str,
) -> CompanyResource:
    resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == resource_key
        )
    )

    if resource is None:
        raise ResourceNotFoundError(
            f"Resource does not exist: {resource_key}"
        )

    return resource


def list_person_resources(
    db: Session,
    person_id: UUID,
) -> list[CompanyResource]:
    person = db.get(Person, person_id)

    if person is None:
        raise ResourceNotFoundError(
            f"Person does not exist: {person_id}"
        )

    return list(
        db.scalars(
            select(CompanyResource)
            .where(
                CompanyResource.person_id == person_id
            )
            .order_by(CompanyResource.created_at)
        )
    )



def resource_audit_data(
    resource: CompanyResource,
) -> dict[str, object]:
    return {
        "person_id": resource.person_id,
        "resource_type": resource.resource_type,
        "resource_key": resource.resource_key,
        "status": resource.status,
        "details_data": resource.details_data,
        "source_action_id": resource.source_action_id,
        "idempotency_key": resource.idempotency_key,
    }
