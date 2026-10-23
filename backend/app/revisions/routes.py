from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.planning.validation import GeneratedPlanValidationError
from app.revisions.schemas import PlanRevisionRequest, PlanRevisionResponse
from app.revisions.service import (
    PlanRevisionApproverError,
    PlanRevisionConflictError,
    PlanRevisionNotFoundError,
    revise_plan,
)


router = APIRouter(tags=["plan revisions"])


@router.post(
    "/plans/{plan_id}/revise",
    response_model=PlanRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_revision(
    plan_id: UUID,
    request: PlanRevisionRequest,
    db: Session = Depends(get_db),
) -> PlanRevisionResponse:
    try:
        return revise_plan(
            db,
            plan_id,
            request.plan_data,
            request.correction_summary,
        )
    except PlanRevisionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlanRevisionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (PlanRevisionApproverError, GeneratedPlanValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
