from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.execution.n8n_client import N8NDispatchError
from app.execution.schemas import PlanExecutionResponse
from app.execution.service import (
    ActionPayloadError,
    ActionVerificationError,
    ExecutionStateConflictError,
    ExecutionTargetNotFoundError,
    execute_approved_plan,
    retry_failed_plan,
)


router = APIRouter(
    prefix="/plans",
    tags=["execution"],
)


@router.post(
    "/{plan_id}/execute",
    response_model=PlanExecutionResponse,
)
def execute_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
) -> PlanExecutionResponse:
    try:
        case, actions = execute_approved_plan(
            db,
            plan_id,
        )

        return PlanExecutionResponse(
            plan_id=plan_id,
            case_id=case.id,
            case_status=case.status,
            actions=actions,
        )

    except ExecutionTargetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ExecutionStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except ActionPayloadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except ActionVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    except N8NDispatchError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

@router.post(
    "/{plan_id}/retry",
    response_model=PlanExecutionResponse,
)
def retry_plan_execution(
    plan_id: UUID,
    db: Session = Depends(get_db),
) -> PlanExecutionResponse:
    try:
        case, actions = retry_failed_plan(
            db,
            plan_id,
        )

        return PlanExecutionResponse(
            plan_id=plan_id,
            case_id=case.id,
            case_status=case.status,
            actions=actions,
        )

    except ExecutionTargetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ExecutionStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except ActionPayloadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except ActionVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    except N8NDispatchError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
