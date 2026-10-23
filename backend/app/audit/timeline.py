from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import PolicyLinkSubjectType
from app.models import (
    Approval,
    AuditEvent,
    Case,
    CaseAction,
    CasePlan,
    LearningRecord,
    PolicyImpact,
    PolicyLink,
)


class AuditTimelineNotFoundError(ValueError):
    pass


def _case_entity_ids(db: Session, case_id: UUID) -> set[UUID]:
    case = db.get(Case, case_id)
    if case is None:
        raise AuditTimelineNotFoundError(f"Case does not exist: {case_id}")

    ids: set[UUID] = {case.id}

    plan_ids = set(
        db.scalars(
            select(CasePlan.id).where(CasePlan.case_id == case_id)
        )
    )
    ids.update(plan_ids)

    action_ids = set(
        db.scalars(
            select(CaseAction.id).where(CaseAction.case_id == case_id)
        )
    )
    ids.update(action_ids)

    if plan_ids:
        approval_ids = set(
            db.scalars(
                select(Approval.id).where(Approval.target_id.in_(plan_ids))
            )
        )
        ids.update(approval_ids)

    learning_ids = set(
        db.scalars(
            select(LearningRecord.id).where(
                LearningRecord.source_case_id == case_id
            )
        )
    )
    ids.update(learning_ids)

    if learning_ids:
        learning_approval_ids = set(
            db.scalars(
                select(Approval.id).where(
                    Approval.target_id.in_(learning_ids)
                )
            )
        )
        ids.update(learning_approval_ids)

    if plan_ids or learning_ids:
        target_ids = set(plan_ids) | set(learning_ids)
        impact_ids = set(
            db.scalars(
                select(PolicyImpact.id).where(
                    PolicyImpact.target_id.in_(target_ids)
                )
            )
        )
        ids.update(impact_ids)

    return ids


def get_case_timeline(
    db: Session,
    case_id: UUID,
) -> list[AuditEvent]:
    entity_ids = _case_entity_ids(db, case_id)

    events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                or_(
                    AuditEvent.correlation_id == case_id,
                    AuditEvent.entity_id.in_(entity_ids),
                )
            )
            .order_by(
                AuditEvent.occurred_at.asc(),
                AuditEvent.id.asc(),
            )
        )
    )

    seen: set[UUID] = set()
    unique: list[AuditEvent] = []
    for event in events:
        if event.id in seen:
            continue
        seen.add(event.id)
        unique.append(event)

    return unique


def _case_has_policy_links(db: Session, case_id: UUID) -> bool:
    plan_ids = list(
        db.scalars(
            select(CasePlan.id).where(CasePlan.case_id == case_id)
        )
    )
    learning_ids = list(
        db.scalars(
            select(LearningRecord.id).where(
                LearningRecord.source_case_id == case_id
            )
        )
    )

    conditions = []

    if plan_ids:
        conditions.append(
            (
                PolicyLink.subject_type == PolicyLinkSubjectType.PLAN
            )
            & (PolicyLink.subject_id.in_(plan_ids))
        )

    if learning_ids:
        conditions.append(
            (
                PolicyLink.subject_type == PolicyLinkSubjectType.LEARNING
            )
            & (PolicyLink.subject_id.in_(learning_ids))
        )

    if not conditions:
        return False

    return (
        db.scalar(
            select(PolicyLink.id)
            .where(or_(*conditions))
            .limit(1)
        )
        is not None
    )


def _events_contain_evidence(events: list[AuditEvent]) -> bool:
    evidence_keys = {
        "evidence_ids",
        "current_evidence_ids",
        "policy_version_ids",
        "policy_version_id",
        "policy_links",
    }

    for event in events:
        payload = event.evidence_data or {}
        if any(
            key in payload and payload.get(key)
            for key in evidence_keys
        ):
            return True

    return False


def audit_coverage(
    db: Session,
    case_id: UUID,
) -> tuple[list[AuditEvent], dict[str, bool], list[str], bool]:
    case = db.get(Case, case_id)
    if case is None:
        raise AuditTimelineNotFoundError(f"Case does not exist: {case_id}")

    events = get_case_timeline(db, case_id)
    types = {event.event_type.upper() for event in events}

    def has_any(*needles: str) -> bool:
        return any(
            any(needle in event_type for needle in needles)
            for event_type in types
        )

    evidence_or_policy_link = (
        _case_has_policy_links(db, case_id)
        or _events_contain_evidence(events)
        or has_any("EVIDENCE", "POLICY", "RETRIEV")
    )

    groups = {
        "case_created": has_any("CASE_CREATED"),
        "plan_generated_or_revised": has_any(
            "PLAN_GENERATED",
            "CASE_PLAN_GENERATED",
            "PLAN_CREATED",
            "PLAN_REVISED",
            "POLICY_IMPACT_REGENERATED",
        ),
        "approval_activity": has_any(
            "APPROVAL",
            "PLAN_APPROVED",
            "PLAN_REJECTED",
            "PLAN_SUBMITTED_FOR_APPROVAL",
        ),
        "evidence_or_policy_link": evidence_or_policy_link,
        "execution_dispatch": has_any(
            "ACTION_DISPATCH",
            "DISPATCHED",
            "N8N",
        ),
        "verification": has_any(
            "VERIFICATION",
            "VERIFIED",
        ),
        "learning_activity": has_any(
            "LEARNING",
            "HANDOVER",
        ),
        "policy_guardian_activity": has_any(
            "POLICY_IMPACT",
            "POLICY_VERSION",
            "POLICY_VECTOR",
        ),
    }

    state = case.status.value
    required = {
        "case_created",
        "plan_generated_or_revised",
        "approval_activity",
        "evidence_or_policy_link",
    }

    if state in {"EXECUTING", "COMPLETED", "FAILED", "HUMAN_REVIEW"}:
        required.update({"execution_dispatch", "verification"})

    missing = sorted(key for key in required if not groups[key])
    return events, groups, missing, not missing
