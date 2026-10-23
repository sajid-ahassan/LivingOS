from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.handover.schemas import (
    HandoverDecisionRequest,
    HandoverDecisionResponse,
    HandoverGenerateRequest,
    HandoverGenerateResponse,
)
from app.handover.service import (
    HandoverConflictError,
    HandoverNotFoundError,
    decide_handover,
    generate_handover,
)


router = APIRouter(tags=["handover"])


@router.post(
    "/cases/{case_id}/handover",
    response_model=HandoverGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_handover(
    case_id: UUID,
    request: HandoverGenerateRequest,
    db: Session = Depends(get_db),
) -> HandoverGenerateResponse:
    try:
        record, approval, document = generate_handover(db, case_id, request)
        return HandoverGenerateResponse(
            learning_record_id=record.id,
            approval_id=approval.id,
            case_id=record.source_case_id,
            plan_id=record.source_plan_id,
            status=record.status,
            approval_status=approval.status,
            handover=document,
        )
    except HandoverNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except HandoverConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/handover-approvals/{approval_id}/decision",
    response_model=HandoverDecisionResponse,
)
def review_handover(
    approval_id: UUID,
    request: HandoverDecisionRequest,
    db: Session = Depends(get_db),
) -> HandoverDecisionResponse:
    try:
        approval, record = decide_handover(
            db,
            approval_id,
            request.decided_by,
            request.decision,
            request.comment,
        )
        return HandoverDecisionResponse(
            approval_id=approval.id,
            learning_record_id=record.id,
            approval_status=approval.status,
            learning_status=record.status,
            comment=approval.comment,
            decided_at=approval.decided_at,
        )
    except HandoverNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except HandoverConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
