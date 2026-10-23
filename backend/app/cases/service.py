from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.schemas import (
    CaseCreateRequest,
    CaseTriageResponse,
)
from app.cases.triage import find_missing_case_facts
from app.enums import AppRole, AuditActorType, CaseState
from app.models import Case, Person


ALLOWED_CASE_CREATORS = {
    AppRole.HR_MANAGER,
    AppRole.LINE_MANAGER,
    AppRole.ADMIN,
}


class PersonNotFoundError(ValueError):
    pass


class CasePermissionError(ValueError):
    pass


class CaseStateConflictError(ValueError):
    pass


def create_case(
    db: Session,
    request: CaseCreateRequest,
) -> Case:
    subject = db.get(Person, request.subject_person_id)

    if subject is None:
        raise PersonNotFoundError(
            f"Subject person does not exist: "
            f"{request.subject_person_id}"
        )

    creator = db.get(Person, request.created_by_id)

    if creator is None:
        raise PersonNotFoundError(
            f"Case creator does not exist: "
            f"{request.created_by_id}"
        )

    if creator.app_role not in ALLOWED_CASE_CREATORS:
        raise CasePermissionError(
            f"{creator.app_role.value} cannot create cases."
        )

    case = Case(
        case_type=request.case_type,
        subject_person_id=request.subject_person_id,
        created_by_id=request.created_by_id,
        status=CaseState.NEW,
        priority=request.priority,
        case_facts=dict(request.case_facts),
    )

    db.add(case)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.USER,
            actor_id=creator.id,
            event_type="CASE_CREATED",
            entity_type="case",
            entity_id=case.id,
            before_data=None,
            after_data={
                "case_type": case.case_type,
                "subject_person_id": case.subject_person_id,
                "created_by_id": case.created_by_id,
                "status": case.status,
                "priority": case.priority,
                "case_facts": case.case_facts,
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(case)

    except Exception:
        db.rollback()
        raise

    return case





class CaseNotFoundError(ValueError):
    pass


def get_case(
    db: Session,
    case_id: UUID,
) -> Case:
    case = db.get(Case, case_id)

    if case is None:
        raise CaseNotFoundError(
            f"Case does not exist: {case_id}"
        )

    return case




def triage_case(
    db: Session,
    case_id: UUID,
) -> CaseTriageResponse:
    case = get_case(db, case_id)

    allowed_states = {
        CaseState.NEW,
        CaseState.HUMAN_REVIEW,
    }

    if case.status not in allowed_states:
        raise CaseStateConflictError(
            f"Cannot triage a case in {case.status.value} state."
        )

    previous_status = case.status
    missing_fields = find_missing_case_facts(case)

    current_status = (
        CaseState.HUMAN_REVIEW
        if missing_fields
        else CaseState.PLANNING
    )

    result = CaseTriageResponse(
        case_id=case.id,
        ready_for_planning=not missing_fields,
        missing_fields=missing_fields,
        previous_status=previous_status,
        current_status=current_status,
    )

    if previous_status == current_status:
        return result

    case.status = current_status
    case.failure_reason = (
        f"Missing required facts: {', '.join(missing_fields)}"
        if missing_fields
        else None
    )

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="CASE_TRIAGED",
            entity_type="case",
            entity_id=case.id,
            before_data={
                "status": previous_status,
            },
            after_data={
                "status": current_status,
                "failure_reason": case.failure_reason,
            },
            evidence_data={
                "missing_fields": missing_fields,
                "rule_type": "DETERMINISTIC_REQUIRED_FIELDS",
            },
            correlation_id=case.id,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return result