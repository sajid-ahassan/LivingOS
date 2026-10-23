from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.schemas import (
    AuditCoverageResponse,
    CaseAuditTimelineResponse,
)
from app.audit.timeline import (
    AuditTimelineNotFoundError,
    audit_coverage,
    get_case_timeline,
)
from app.database import get_db


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/cases/{case_id}/timeline",
    response_model=CaseAuditTimelineResponse,
)
def case_audit_timeline(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> CaseAuditTimelineResponse:
    try:
        events = get_case_timeline(db, case_id)
        return CaseAuditTimelineResponse(
            case_id=case_id,
            total_events=len(events),
            event_types=sorted({event.event_type for event in events}),
            events=events,
        )
    except AuditTimelineNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/cases/{case_id}/coverage",
    response_model=AuditCoverageResponse,
)
def case_audit_coverage(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> AuditCoverageResponse:
    try:
        events, groups, missing, complete = audit_coverage(db, case_id)
        return AuditCoverageResponse(
            case_id=case_id,
            total_events=len(events),
            present_groups=groups,
            missing_groups=missing,
            complete_for_current_case_state=complete,
        )
    except AuditTimelineNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
