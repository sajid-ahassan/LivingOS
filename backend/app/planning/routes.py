from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.cases.service import CaseNotFoundError
from app.database import get_db
from app.planning.schemas import CasePlanResponse
from app.planning.service import (
    CasePlanningError,
    PolicyVersionNotFoundError,
    create_case_plan,
)
from app.planning.validation import (
    GeneratedPlanValidationError,
)


router = APIRouter(
    prefix="/cases",
    tags=["planning"],
)


@router.post(
    "/{case_id}/plan",
    response_model=CasePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> CasePlanResponse:
    try:
        return create_case_plan(
            db,
            case_id,
        )

    except CaseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except CasePlanningError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except GeneratedPlanValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except PolicyVersionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error