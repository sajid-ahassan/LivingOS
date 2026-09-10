from app.enums import ActionType, ResourceState, ResourceType

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CaseAction, CompanyResource, Person
from app.schemas import MockResourceApplyRequest

from uuid import UUID

ACTION_STATE_MAP = {
    ActionType.CREATE: ResourceState.ACTIVE,
    ActionType.ASSIGN: ResourceState.ASSIGNED,
    ActionType.DISABLE: ResourceState.DISABLED,
    ActionType.REVOKE: ResourceState.REVOKED,
    ActionType.REASSIGN: ResourceState.REASSIGNED,
    ActionType.REQUEST_RETURN: ResourceState.RETURN_REQUESTED,
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

    source_action = db.get(CaseAction, request.action_id)

    resource = CompanyResource(
        person_id=request.person_id,
        resource_type=request.resource_type,
        resource_key=request.resource_key,
        status=get_target_resource_state(
            request.action_type
        ),
        details_data=dict(request.requested_data),
        source_action_id=(
            source_action.id
            if source_action is not None
            else None
        ),
        idempotency_key=request.idempotency_key,
    )

    db.add(resource)

    try:
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

    source_action = db.get(CaseAction, request.action_id)

    resource.status = get_target_resource_state(
        request.action_type
    )
    resource.details_data = updated_details
    resource.idempotency_key = request.idempotency_key

    if source_action is not None:
        resource.source_action_id = source_action.id

    try:
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