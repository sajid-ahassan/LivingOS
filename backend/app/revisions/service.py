from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.policy_context import retrieve_case_policy_context
from app.enums import (
    ActionState,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CaseState,
    PlanState,
)
from app.models import Approval, Case, CasePlan, CompanyResource, Person
from app.planning.schemas import GeneratedCasePlan
from app.planning.service import build_case_action, build_policy_links
from app.planning.validation import validate_generated_plan
from app.revisions.schemas import PlanRevisionResponse


class PlanRevisionNotFoundError(ValueError):
    pass


class PlanRevisionConflictError(ValueError):
    pass


class PlanRevisionApproverError(ValueError):
    pass


REVISION_ALLOWED_CASE_STATES = {
    CaseState.PLANNING,
    CaseState.PENDING_APPROVAL,
    CaseState.APPROVED,
    CaseState.HUMAN_REVIEW,
}

REVISION_ALLOWED_PLAN_STATES = {
    PlanState.DRAFT,
    PlanState.PENDING_APPROVAL,
    PlanState.APPROVED,
    PlanState.REJECTED,
}


def _next_revision(db: Session, case_id: UUID) -> int:
    current = db.scalar(
        select(func.max(CasePlan.revision)).where(CasePlan.case_id == case_id)
    )
    return (current or 0) + 1


def _resolve_approver(db: Session, case: Case) -> Person:
    subject = db.get(Person, case.subject_person_id)
    if subject is None:
        raise PlanRevisionApproverError("Case subject does not exist.")

    manager_id = subject.manager_id or (case.case_facts or {}).get("manager_id")
    if not manager_id:
        raise PlanRevisionApproverError(
            "A manager is required before a revised plan can be submitted."
        )

    approver = db.get(Person, UUID(str(manager_id)))
    if approver is None:
        raise PlanRevisionApproverError("Assigned manager does not exist.")

    return approver


def _cancel_parent_pending_approval(db: Session, parent_plan: CasePlan) -> None:
    approval = db.scalar(
        select(Approval).where(
            Approval.target_type == ApprovalTargetType.PLAN,
            Approval.target_id == parent_plan.id,
            Approval.status == ApprovalState.PENDING,
        )
    )
    if approval is not None:
        approval.status = ApprovalState.REJECTED
        approval.comment = "Superseded by a manager revision."


def revise_plan(
    db: Session,
    plan_id: UUID,
    replacement: GeneratedCasePlan,
    correction_summary: str,
) -> PlanRevisionResponse:
    parent = db.get(CasePlan, plan_id)
    if parent is None:
        raise PlanRevisionNotFoundError(f"Plan does not exist: {plan_id}")

    case = db.get(Case, parent.case_id)
    if case is None:
        raise PlanRevisionNotFoundError(f"Case does not exist: {parent.case_id}")

    if parent.status not in REVISION_ALLOWED_PLAN_STATES:
        raise PlanRevisionConflictError(
            f"Plan cannot be revised from {parent.status.value}."
        )

    if case.status not in REVISION_ALLOWED_CASE_STATES:
        raise PlanRevisionConflictError(
            f"Case cannot be revised from {case.status.value}."
        )

    if any(action.status in {ActionState.DISPATCHED, ActionState.SUCCEEDED, ActionState.VERIFIED}
           for action in parent.actions):
        raise PlanRevisionConflictError(
            "A plan cannot be revised after execution has started."
        )

    policy_context = retrieve_case_policy_context(db, case)
    resources = db.scalars(
        select(CompanyResource).where(
            CompanyResource.person_id == case.subject_person_id
        )
    ).all()

    validate_generated_plan(
        replacement,
        case=case,
        policy_context=policy_context,
        resources=list(resources),
        get_person=lambda person_id: db.get(Person, person_id),
    )

    approver = _resolve_approver(db, case)

    try:
        new_plan = CasePlan(
            case_id=case.id,
            revision=_next_revision(db, case.id),
            status=PlanState.PENDING_APPROVAL,
            plan_data=jsonable_encoder(replacement.model_dump()),
            summary=replacement.summary,
            parent_plan_id=parent.id,
            correction_summary=correction_summary.strip(),
        )
        db.add(new_plan)
        db.flush()

        new_actions = [
            build_case_action(case=case, plan=new_plan, action=action)
            for action in replacement.actions
        ]
        new_links = build_policy_links(
            db,
            new_plan,
            replacement,
            policy_context,
        )
        db.add_all(new_actions)
        db.add_all(new_links)

        old_status = parent.status
        parent.status = PlanState.SUPERSEDED
        for action in parent.actions:
            if action.status in {ActionState.PENDING, ActionState.FAILED, ActionState.RETRYING}:
                action.status = ActionState.SKIPPED
                action.error_message = "Parent plan was superseded by a manager revision."

        _cancel_parent_pending_approval(db, parent)

        approval = Approval(
            target_type=ApprovalTargetType.PLAN,
            target_id=new_plan.id,
            requested_by=case.created_by_id,
            assigned_to=approver.id,
            status=ApprovalState.PENDING,
        )
        db.add(approval)
        case.status = CaseState.PENDING_APPROVAL
        case.failure_reason = None
        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.USER,
            actor_id=approver.id,
            event_type="PLAN_REVISED",
            entity_type="case_plan",
            entity_id=new_plan.id,
            before_data={
                "parent_plan_id": str(parent.id),
                "parent_status": old_status.value,
                "parent_revision": parent.revision,
            },
            after_data={
                "new_plan_id": str(new_plan.id),
                "new_revision": new_plan.revision,
                "new_status": new_plan.status.value,
                "case_status": case.status.value,
            },
            evidence_data={
                "correction_summary": correction_summary.strip(),
                "current_evidence_ids": sorted({
                    evidence_id
                    for action in replacement.actions
                    for evidence_id in action.evidence_ids
                }),
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(new_plan)
        db.refresh(approval)

        return PlanRevisionResponse(
            id=new_plan.id,
            case_id=new_plan.case_id,
            revision=new_plan.revision,
            status=new_plan.status,
            summary=new_plan.summary,
            plan_data=new_plan.plan_data,
            parent_plan_id=parent.id,
            correction_summary=new_plan.correction_summary or "",
            approval_id=approval.id,
            approval_status=approval.status,
            assigned_to=approval.assigned_to,
            created_at=new_plan.created_at,
            updated_at=new_plan.updated_at,
        )
    except Exception:
        db.rollback()
        raise
