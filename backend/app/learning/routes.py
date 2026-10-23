from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.learning.schemas import (
    LearningCandidateCreateRequest,
    LearningCandidateCreateResponse,
    LearningDecisionRequest,
    LearningDecisionResponse,
    LearningEvidence,
    LearningIndexResponse,
    LearningSearchRequest,
    LearningSearchResponse,
)
from app.learning.service import (
    LearningConflictError,
    LearningNotFoundError,
    create_plan_correction_candidate,
    decide_learning_candidate,
    index_approved_learning,
    search_approved_learning,
)


router = APIRouter(tags=["learning"])


@router.post(
    "/cases/{case_id}/learning/candidate",
    response_model=LearningCandidateCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_candidate(
    case_id: UUID,
    request: LearningCandidateCreateRequest,
    db: Session = Depends(get_db),
) -> LearningCandidateCreateResponse:
    try:
        record, approval, candidate, duplicate_warning = create_plan_correction_candidate(
            db,
            case_id,
            request.assigned_to,
        )
        return LearningCandidateCreateResponse(
            learning_record_id=record.id,
            approval_id=approval.id,
            source_case_id=record.source_case_id,
            source_plan_id=record.source_plan_id,
            trigger_type=record.trigger_type,
            learning_status=record.status,
            approval_status=approval.status,
            candidate=candidate,
            duplicate_warning=duplicate_warning,
        )
    except LearningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LearningConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/learning-approvals/{approval_id}/decision",
    response_model=LearningDecisionResponse,
)
def review_learning_candidate(
    approval_id: UUID,
    request: LearningDecisionRequest,
    db: Session = Depends(get_db),
) -> LearningDecisionResponse:
    try:
        approval, record = decide_learning_candidate(
            db,
            approval_id,
            request.decided_by,
            request.decision,
            request.comment,
        )
        return LearningDecisionResponse(
            approval_id=approval.id,
            learning_record_id=record.id,
            approval_status=approval.status,
            learning_status=record.status,
            qdrant_point_id=record.qdrant_point_id,
            comment=approval.comment,
            decided_at=approval.decided_at,
        )
    except LearningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LearningConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/learning/{learning_record_id}/index",
    response_model=LearningIndexResponse,
)
def index_learning_record(
    learning_record_id: UUID,
    db: Session = Depends(get_db),
) -> LearningIndexResponse:
    try:
        record, evidence_id, sanitized, policy_version_ids = index_approved_learning(
            db,
            learning_record_id,
        )
    except LearningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LearningConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if record.qdrant_point_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning was approved in PostgreSQL but Qdrant indexing did not complete.",
        )

    return LearningIndexResponse(
        learning_record_id=record.id,
        status=record.status,
        qdrant_point_id=record.qdrant_point_id,
        evidence_id=evidence_id,
        sanitized_before_indexing=sanitized,
        policy_version_ids=policy_version_ids,
    )


@router.post(
    "/learning/search",
    response_model=LearningSearchResponse,
)
def search_learning(
    request: LearningSearchRequest,
) -> LearningSearchResponse:
    results = search_approved_learning(request)
    return LearningSearchResponse(
        query=request.query,
        results=[
            LearningEvidence(
                evidence_id=item.evidence_id,
                learning_id=item.learning_id,
                trigger_type=item.trigger_type,
                text=item.text,
                score=item.score,
                policy_version_ids=item.policy_version_ids,
                scope=item.scope,
            )
            for item in results
        ],
    )
