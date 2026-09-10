from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.mock_company.service import (
    IdempotencyConflictError,
    ResourceConflictError,
    ResourceNotFoundError,
    apply_resource_action,
    get_resource_by_key,
    list_person_resources,
)
from app.schemas import (
    CompanyResourceResponse,
    MockResourceApplyRequest,
    MockResourceApplyResponse,
)


router = APIRouter(
    prefix="/mock",
    tags=["Mock Company"],
)


@router.post(
    "/resources/apply",
    response_model=MockResourceApplyResponse,
)
def apply_resource(
    request: MockResourceApplyRequest,
    db: Session = Depends(get_db),
) -> MockResourceApplyResponse:
    try:
        resource, already_existed = apply_resource_action(
            db,
            request,
        )
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ResourceConflictError,
        IdempotencyConflictError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return MockResourceApplyResponse(
        resource_id=resource.id,
        resource_key=resource.resource_key,
        resource_status=resource.status,
        already_existed=already_existed,
    )


@router.get(
    "/resources/{resource_key:path}",
    response_model=CompanyResourceResponse,
)
def read_resource(
    resource_key: str,
    db: Session = Depends(get_db),
) -> CompanyResourceResponse:
    try:
        return get_resource_by_key(
            db,
            resource_key,
        )
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/people/{person_id}/resources",
    response_model=list[CompanyResourceResponse],
)
def read_person_resources(
    person_id: UUID,
    db: Session = Depends(get_db),
) -> list[CompanyResourceResponse]:
    try:
        return list_person_resources(
            db,
            person_id,
        )
    except ResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error