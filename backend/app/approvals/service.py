from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.enums import (
    AppRole,
    ActionState,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CaseState,
    PlanState,
)
from app.models import Approval, Case, CasePlan, Person
from app.notifications.service import notify


ALLOWED_APPROVER_ROLES = {
    AppRole.HR_MANAGER,
    AppRole.LINE_MANAGER,
    AppRole.ADMIN,
}


class ApprovalTargetNotFoundError(ValueError):
    pass


class ApprovalStateConflictError(ValueError):
    pass


class InvalidApproverError(ValueError):
    pass


class ApprovalNotFoundError(ValueError):
    pass


class ApprovalDecisionPermissionError(ValueError):
    pass


def validate_plan_submission(
    db: Session,
    plan_id: UUID,
    assigned_to: UUID,
) -> tuple[CasePlan, Case, Person]:
    plan = db.get(CasePlan, plan_id)

    if plan is None:
        raise ApprovalTargetNotFoundError(
            f"Plan does not exist: {plan_id}"
        )

    case = db.get(Case, plan.case_id)

    if case is None:
        raise ApprovalTargetNotFoundError(
            f"Case does not exist: {plan.case_id}"
        )

    if plan.status != PlanState.DRAFT:
        raise ApprovalStateConflictError(
            f"Only a DRAFT plan can be submitted. "
            f"Current status: {plan.status.value}"
        )

    if case.status != CaseState.PLANNING:
        raise ApprovalStateConflictError(
            f"Case must be in PLANNING state. "
            f"Current status: {case.status.value}"
        )

    approver = db.get(Person, assigned_to)

    if approver is None:
        raise InvalidApproverError(
            f"Approver does not exist: {assigned_to}"
        )

    if approver.app_role not in ALLOWED_APPROVER_ROLES:
        raise InvalidApproverError(
            f"{approver.app_role.value} cannot approve plans."
        )

    if approver.id == case.subject_person_id:
        raise InvalidApproverError(
            "The subject person cannot approve their own plan."
        )

    return plan, case, approver





def submit_plan_for_approval(
    db: Session,
    plan_id: UUID,
    assigned_to: UUID,
) -> Approval:
    plan, case, approver = validate_plan_submission(
        db,
        plan_id,
        assigned_to,
    )

    approval = Approval(
        target_type=ApprovalTargetType.PLAN,
        target_id=plan.id,
        requested_by=case.created_by_id,
        assigned_to=approver.id,
        status=ApprovalState.PENDING,
    )

    try:
        plan.status = PlanState.PENDING_APPROVAL
        case.status = CaseState.PENDING_APPROVAL

        db.add(approval)
        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.USER,
            actor_id=case.created_by_id,
            event_type="PLAN_SUBMITTED_FOR_APPROVAL",
            entity_type="approval",
            entity_id=approval.id,
            before_data={
                "plan_status": PlanState.DRAFT.value,
                "case_status": CaseState.PLANNING.value,
            },
            after_data={
                "approval_status": approval.status.value,
                "plan_status": plan.status.value,
                "case_status": case.status.value,
                "assigned_to": str(approver.id),
            },
            evidence_data={
                "plan_id": str(plan.id),
                "plan_revision": plan.revision,
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(approval)

    except Exception:
        db.rollback()
        raise

    # After the commit, and best-effort: a failed message never undoes the
    # approval request.
    notify(
        event_type="APPROVAL_REQUESTED",
        title=f"Approval needed: {case.case_type.value} plan revision {plan.revision}",
        summary=plan.summary or "A plan is waiting for your decision.",
        link_path=f"workspace.html?case={case.id}",
        audience=approver.name,
    )

    return approval



def validate_approval_decision(
    db: Session,
    approval_id: UUID,
    decided_by: UUID,
) -> tuple[Approval, CasePlan, Case]:
    approval = db.get(Approval, approval_id)

    if approval is None:
        raise ApprovalNotFoundError(
            f"Approval does not exist: {approval_id}"
        )

    if approval.target_type != ApprovalTargetType.PLAN:
        raise ApprovalStateConflictError(
            "This approval does not target a case plan."
        )

    if approval.status != ApprovalState.PENDING:
        raise ApprovalStateConflictError(
            f"Approval has already been decided: "
            f"{approval.status.value}"
        )

    if approval.assigned_to != decided_by:
        raise ApprovalDecisionPermissionError(
            "Only the assigned approver can decide "
            "this approval."
        )

    plan = db.get(CasePlan, approval.target_id)

    if plan is None:
        raise ApprovalTargetNotFoundError(
            f"Target plan does not exist: "
            f"{approval.target_id}"
        )

    case = db.get(Case, plan.case_id)

    if case is None:
        raise ApprovalTargetNotFoundError(
            f"Case does not exist: {plan.case_id}"
        )

    if plan.status != PlanState.PENDING_APPROVAL:
        raise ApprovalStateConflictError(
            f"Plan is not awaiting approval. "
            f"Current status: {plan.status.value}"
        )

    if case.status != CaseState.PENDING_APPROVAL:
        raise ApprovalStateConflictError(
            f"Case is not awaiting approval. "
            f"Current status: {case.status.value}"
        )

    return approval, plan, case






def decide_plan_approval(
    db: Session,
    approval_id: UUID,
    decided_by: UUID,
    decision: ApprovalState,
    comment: str | None,
) -> Approval:
    if decision not in {
        ApprovalState.APPROVED,
        ApprovalState.REJECTED,
    }:
        raise ApprovalStateConflictError(
            "Decision must be APPROVED or REJECTED."
        )

    if decision == ApprovalState.REJECTED and not (
        comment and comment.strip()
    ):
        raise ApprovalStateConflictError(
            "A rejection comment is required."
        )

    approval, plan, case = validate_approval_decision(
        db,
        approval_id,
        decided_by,
    )

    try:
        approval.status = decision
        approval.comment = comment
        approval.decided_at = datetime.now(timezone.utc)

        if decision == ApprovalState.APPROVED:
            plan.status = PlanState.APPROVED
            case.status = CaseState.APPROVED
            case.failure_reason = None
            event_type = "PLAN_APPROVED"

        else:
            plan.status = PlanState.REJECTED
            case.status = CaseState.HUMAN_REVIEW
            case.failure_reason = (
                comment or "The generated plan was rejected."
            )
            event_type = "PLAN_REJECTED"

            for action in plan.actions:
                action.status = ActionState.SKIPPED
                action.error_message = "Parent plan was rejected."

        record_audit_event(
            db,
            actor_type=AuditActorType.USER,
            actor_id=decided_by,
            event_type=event_type,
            entity_type="approval",
            entity_id=approval.id,
            before_data={
                "approval_status": ApprovalState.PENDING.value,
                "plan_status": PlanState.PENDING_APPROVAL.value,
                "case_status": CaseState.PENDING_APPROVAL.value,
            },
            after_data={
                "approval_status": approval.status.value,
                "plan_status": plan.status.value,
                "case_status": case.status.value,
            },
            evidence_data={
                "plan_id": str(plan.id),
                "comment": comment,
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(approval)



    except Exception:
        db.rollback()
        raise

    return approval
