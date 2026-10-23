from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.cases.schemas import (
    CaseCreateRequest,
    CasePolicyContextResponse,
    CaseResponse,
    CaseTriageResponse,
)

from app.cases.policy_context import (
    PolicyContextStateError,
    PolicyEvidenceNotFoundError,
    retrieve_case_policy_context,
)

from app.cases.service import (
    CaseNotFoundError,
    CasePermissionError,
    CaseStateConflictError,
    PersonNotFoundError,
    create_case,
    get_case,
    triage_case,
)
from app.database import get_db


router = APIRouter(
    prefix="/cases",
    tags=["Cases"],
)


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case_route(
    request: CaseCreateRequest,
    db: Session = Depends(get_db),
) -> CaseResponse:
    try:
        return create_case(db, request)

    except PersonNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except CasePermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
)
def get_case_route(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> CaseResponse:
    try:
        return get_case(db, case_id)

    except CaseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error




@router.post(
    "/{case_id}/triage",
    response_model=CaseTriageResponse,
)
def triage_case_route(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> CaseTriageResponse:
    try:
        return triage_case(db, case_id)

    except CaseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except CaseStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error




@router.get(
    "/{case_id}/policy-context",
    response_model=CasePolicyContextResponse,
)
def get_case_policy_context_route(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> CasePolicyContextResponse:
    try:
        case = get_case(db, case_id)

        return retrieve_case_policy_context(
            db,
            case,
            top_k=5,
        )

    except CaseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except PolicyContextStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except PolicyEvidenceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error