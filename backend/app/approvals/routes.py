from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.approvals.schemas import (
    ApprovalDecisionRequest,
    ApprovalResponse,
    PlanSubmissionRequest,
)
from app.approvals.service import (
    ApprovalDecisionPermissionError,
    ApprovalNotFoundError,
    ApprovalStateConflictError,
    ApprovalTargetNotFoundError,
    InvalidApproverError,
    decide_plan_approval,
    submit_plan_for_approval,
)
from app.database import get_db


router = APIRouter(
    tags=["approvals"],
)


@router.post(
    "/plans/{plan_id}/submit",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_plan(
    plan_id: UUID,
    request: PlanSubmissionRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    try:
        return submit_plan_for_approval(
            db,
            plan_id,
            request.assigned_to,
        )

    except ApprovalTargetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ApprovalStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except InvalidApproverError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error



@router.post(
    "/approvals/{approval_id}/decision",
    response_model=ApprovalResponse,
)
def decide_approval(
    approval_id: UUID,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    try:
        return decide_plan_approval(
            db,
            approval_id,
            request.decided_by,
            request.decision,
            request.comment,
        )

    except (
        ApprovalNotFoundError,
        ApprovalTargetNotFoundError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ApprovalDecisionPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    except ApprovalStateConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error