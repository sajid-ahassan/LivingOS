from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.config import get_settings
from app.enums import (
    ActionState,
    ActionType,
    AuditActorType,
    CaseState,
    PlanState,
)
from app.execution.n8n_client import N8NDispatchError, dispatch_to_n8n
from app.github.client import get_read_client
from app.github.keys import generate_public_key
from app.github.targets import build_github_parameters, build_grant_github_parameters
from app.github.verifier import GitHubVerification, verify_github_action
from app.models import Case, CaseAction, CasePlan, CompanyResource
from app.policy_guardian.resource_remediation import resolve_remediated_impact
from app.resource_rules import (
    action_moves_owner,
    successor_from_parameters,
    target_resource_state,
)


MAX_EXECUTION_ATTEMPTS = 2


class ActionPayloadError(ValueError):
    pass


class ExecutionTargetNotFoundError(ValueError):
    pass


class ExecutionStateConflictError(ValueError):
    pass


class ActionVerificationError(RuntimeError):
    pass


def build_n8n_action_payload(
    action: CaseAction,
    case: Case,
) -> dict[str, Any]:
    action_data = action.requested_data or {}
    resource_key = action_data.get("resource_key")

    if not isinstance(resource_key, str) or not resource_key.strip():
        raise ActionPayloadError(
            f"Action {action.id} has no valid resource_key."
        )

    parameters = action_data.get("parameters", {})

    if not isinstance(parameters, dict):
        raise ActionPayloadError(
            f"Action {action.id} parameters must be an object."
        )

    github = action_data.get("github")
    requested_data = {**parameters, "github": github} if github else parameters

    return {
        "action_id": str(action.id),
        "case_id": str(case.id),
        "person_id": str(case.subject_person_id),
        "action_type": action.action_type.value,
        "resource_type": action.resource_type.value,
        "resource_key": resource_key,
        "idempotency_key": action.idempotency_key,
        # n8n routes "github" actions to the GitHub API and the rest to the
        # mock company API.
        "target": "github" if github else "mock",
        "requested_data": requested_data,
    }


def prepare_github_parameters(db: Session, action: CaseAction) -> None:
    """Attach real-GitHub parameters once, before the first dispatch.

    They are stored on the action so a retry reuses the same deploy key and
    title instead of generating a second key.
    """
    action_data = action.requested_data or {}
    if "github" in action_data:
        return

    resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == action_data.get("resource_key")
        )
    )
    if resource is None:
        if action.action_type != ActionType.GRANT_TEMPORARY:
            return
        github = build_grant_github_parameters(
            action_data.get("parameters") or {},
            str(action_data.get("resource_key")),
            settings=get_settings(),
            idempotency_key=action.idempotency_key,
            new_public_key=generate_public_key,
        )
        if github is not None:
            action.requested_data = {**action_data, "github": github}
        return

    github = build_github_parameters(
        action.action_type,
        resource,
        settings=get_settings(),
        idempotency_key=action.idempotency_key,
        new_public_key=generate_public_key,
    )
    if github is not None:
        action.requested_data = {**action_data, "github": github}


def _load_plan_and_case(
    db: Session,
    plan_id: UUID,
) -> tuple[CasePlan, Case]:
    plan = db.get(CasePlan, plan_id)

    if plan is None:
        raise ExecutionTargetNotFoundError(
            f"Plan does not exist: {plan_id}"
        )

    case = db.get(Case, plan.case_id)

    if case is None:
        raise ExecutionTargetNotFoundError(
            f"Case does not exist: {plan.case_id}"
        )

    return plan, case


def _ordered_actions(plan: CasePlan) -> list[CaseAction]:
    try:
        actions = sorted(
            plan.actions,
            key=lambda action: int(
                (action.requested_data or {}).get("sequence", 0)
            ),
        )
        actual_sequences = [
            int((action.requested_data or {}).get("sequence", 0))
            for action in actions
        ]
    except (TypeError, ValueError) as error:
        raise ExecutionStateConflictError(
            "An action has an invalid sequence value."
        ) from error

    if not actions:
        raise ExecutionStateConflictError(
            "The approved plan has no actions."
        )

    if actual_sequences != list(range(1, len(actions) + 1)):
        raise ExecutionStateConflictError(
            "Action sequence must start at 1 and be consecutive."
        )

    return actions


def get_execution_context(
    db: Session,
    plan_id: UUID,
) -> tuple[CasePlan, Case, list[CaseAction]]:
    plan, case = _load_plan_and_case(db, plan_id)

    if plan.status != PlanState.APPROVED:
        raise ExecutionStateConflictError(
            "Plan must be APPROVED before execution. "
            f"Current status: {plan.status.value}"
        )

    if case.status != CaseState.APPROVED:
        raise ExecutionStateConflictError(
            "Case must be APPROVED before execution. "
            f"Current status: {case.status.value}"
        )

    actions = _ordered_actions(plan)
    invalid_actions = [
        str(action.id)
        for action in actions
        if action.status != ActionState.PENDING
    ]

    if invalid_actions:
        raise ExecutionStateConflictError(
            "Some actions are not PENDING: "
            + ", ".join(invalid_actions)
        )

    return plan, case, actions


def get_retry_context(
    db: Session,
    plan_id: UUID,
) -> tuple[CasePlan, Case, list[CaseAction]]:
    plan, case = _load_plan_and_case(db, plan_id)

    if plan.status != PlanState.APPROVED:
        raise ExecutionStateConflictError(
            "Only an APPROVED plan can be resumed."
        )

    if case.status not in {CaseState.FAILED, CaseState.EXECUTING}:
        raise ExecutionStateConflictError(
            f"Case cannot be resumed from {case.status.value} state."
        )

    actions = _ordered_actions(plan)
    resumable_states = {
        ActionState.PENDING,
        ActionState.DISPATCHED,
        ActionState.SUCCEEDED,
        ActionState.VERIFIED,
        ActionState.FAILED,
    }

    if any(action.status not in resumable_states for action in actions):
        raise ExecutionStateConflictError(
            "The plan contains an action that cannot be resumed."
        )

    if not any(
        action.status in {
            ActionState.DISPATCHED,
            ActionState.SUCCEEDED,
            ActionState.FAILED,
        }
        for action in actions
    ):
        raise ExecutionStateConflictError(
            "The plan has no resumable action awaiting verification or retry."
        )

    return plan, case, actions


def _mark_attempt_limit_reached(
    db: Session,
    action: CaseAction,
    case: Case,
) -> None:
    previous_action_status = action.status
    previous_case_status = case.status
    message = (
        f"Action reached the maximum of {MAX_EXECUTION_ATTEMPTS} "
        "execution attempts and requires human review."
    )

    action.status = ActionState.HUMAN_REVIEW
    action.error_message = message
    case.status = CaseState.HUMAN_REVIEW
    case.failure_reason = message

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_ATTEMPTS_EXHAUSTED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={
                "action_status": previous_action_status.value,
                "case_status": previous_case_status.value,
            },
            after_data={
                "action_status": action.status.value,
                "case_status": case.status.value,
                "attempt_count": action.attempt_count,
            },
            evidence_data={"reason": message},
            correlation_id=case.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    raise ExecutionStateConflictError(message)


def execute_single_action(
    db: Session,
    action: CaseAction,
    case: Case,
) -> CaseAction:
    prepare_github_parameters(db, action)
    payload = build_n8n_action_payload(action, case)
    previous_status = action.status

    if previous_status not in {
        ActionState.PENDING,
        ActionState.DISPATCHED,
        ActionState.FAILED,
    }:
        raise ExecutionStateConflictError(
            f"Action {action.id} cannot be executed from "
            f"{previous_status.value} state."
        )

    if action.attempt_count >= MAX_EXECUTION_ATTEMPTS:
        _mark_attempt_limit_reached(db, action, case)

    action.status = ActionState.DISPATCHED
    action.attempt_count += 1
    action.error_message = None

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_DISPATCHED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={"status": previous_status.value},
            after_data={
                "status": action.status.value,
                "attempt_count": action.attempt_count,
            },
            evidence_data={
                "resource_key": payload["resource_key"],
            },
            correlation_id=case.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        result = dispatch_to_n8n(payload)
    except N8NDispatchError as error:
        exhausted = action.attempt_count >= MAX_EXECUTION_ATTEMPTS
        action.status = (
            ActionState.HUMAN_REVIEW if exhausted else ActionState.FAILED
        )
        action.error_message = str(error)
        case.status = (
            CaseState.HUMAN_REVIEW if exhausted else CaseState.FAILED
        )
        case.failure_reason = str(error)

        try:
            record_audit_event(
                db,
                actor_type=AuditActorType.SYSTEM,
                event_type=(
                    "ACTION_ATTEMPTS_EXHAUSTED"
                    if exhausted
                    else "ACTION_FAILED"
                ),
                entity_type="case_action",
                entity_id=action.id,
                before_data={
                    "status": ActionState.DISPATCHED.value,
                },
                after_data={
                    "status": action.status.value,
                    "case_status": case.status.value,
                    "attempt_count": action.attempt_count,
                    "error": str(error),
                },
                evidence_data={
                    "resource_key": payload["resource_key"],
                },
                correlation_id=case.id,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        raise

    action.status = ActionState.SUCCEEDED
    action.result_data = jsonable_encoder(result)
    execution_id = result.get("execution_id") or result.get("n8n_execution_id")
    if execution_id is not None:
        action.n8n_execution_id = str(execution_id)[:120]
    action.error_message = None

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.N8N,
            event_type="ACTION_SUCCEEDED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={
                "status": ActionState.DISPATCHED.value,
            },
            after_data={
                "status": action.status.value,
                "result": action.result_data,
            },
            evidence_data={
                "resource_key": payload["resource_key"],
            },
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return verify_action_resource(db, action, case)


def _expected_person_id(
    action: CaseAction,
    case: Case,
) -> UUID | None:
    parameters = (action.requested_data or {}).get("parameters", {})
    if not action_moves_owner(action.action_type, parameters):
        return case.subject_person_id

    return successor_from_parameters(parameters)


def verify_action_resource(
    db: Session,
    action: CaseAction,
    case: Case,
) -> CaseAction:
    if action.status not in {
        ActionState.SUCCEEDED,
        ActionState.DISPATCHED,
        ActionState.FAILED,
    }:
        raise ExecutionStateConflictError(
            f"Action {action.id} cannot be verified from "
            f"{action.status.value} state."
        )

    action_data = action.requested_data or {}
    expected_key = action_data.get("resource_key")
    expected_person_id = _expected_person_id(action, case)
    expected_state = target_resource_state(
        action.action_type,
        action.resource_type,
    )

    resource = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == expected_key
        )
    )

    problems: list[str] = []
    github_check: GitHubVerification | None = None
    github_params = action_data.get("github")
    if github_params and (
        resource is not None or action.action_type == ActionType.GRANT_TEMPORARY
    ):
        # Real GitHub: n8n's answer is not evidence. The backend checks
        # GitHub with its own read-only token and only then records the
        # change on the resource itself.
        github_check = verify_github_action(
            action.action_type, github_params, get_read_client()
        )
        if github_check.ok:
            if resource is None:
                resource = _new_github_grant(db, action, case, github_params)
            _apply_verified_github_change(resource, action, github_check)
            db.flush()
        else:
            problems.extend(github_check.problems)

    if resource is None:
        problems.append("resource was not found")
    else:
        if resource.resource_type != action.resource_type:
            problems.append("resource type does not match")
        if resource.person_id != expected_person_id:
            problems.append("resource owner does not match")
        if resource.status != expected_state:
            problems.append(
                "resource state is "
                f"{resource.status.value}, expected {expected_state.value}"
            )
        if resource.source_action_id != action.id:
            problems.append("source action does not match")

    if problems:
        previous_status = action.status
        message = (
            f"Verification failed for action {action.id}: "
            + "; ".join(problems)
        )
        exhausted = action.attempt_count >= MAX_EXECUTION_ATTEMPTS
        action.status = (
            ActionState.HUMAN_REVIEW if exhausted else ActionState.FAILED
        )
        action.error_message = message
        action.verification_data = {
            "verified": False,
            "resource_key": expected_key,
            "expected_status": expected_state.value,
            "problems": problems,
            "source": "github" if github_params else "mock_company",
        }
        if github_check is not None:
            action.verification_data["github_observed"] = github_check.observed
        case.status = (
            CaseState.HUMAN_REVIEW if exhausted else CaseState.FAILED
        )
        case.failure_reason = message

        try:
            record_audit_event(
                db,
                actor_type=AuditActorType.SYSTEM,
                event_type=(
                    "ACTION_VERIFICATION_ATTEMPTS_EXHAUSTED"
                    if exhausted
                    else "ACTION_VERIFICATION_FAILED"
                ),
                entity_type="case_action",
                entity_id=action.id,
                before_data={"status": previous_status.value},
                after_data={
                    "status": action.status.value,
                    "verification_data": action.verification_data,
                },
                evidence_data={"resource_key": expected_key},
                correlation_id=case.id,
            )
            db.commit()
            db.refresh(action)
        except Exception:
            db.rollback()
            raise

        raise ActionVerificationError(message)

    previous_status = action.status
    action.status = ActionState.VERIFIED
    action.error_message = None
    action.verification_data = {
        "verified": True,
        "resource_id": str(resource.id),
        "resource_key": resource.resource_key,
        "resource_type": resource.resource_type.value,
        "resource_status": resource.status.value,
        "person_id": str(resource.person_id),
        "source_action_id": str(resource.source_action_id),
        "source": "github" if github_params else "mock_company",
    }
    if github_check is not None:
        action.verification_data["github_observed"] = github_check.observed

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_VERIFIED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={"status": previous_status.value},
            after_data={
                "status": action.status.value,
                "verification_data": action.verification_data,
            },
            evidence_data={
                "resource_id": str(resource.id),
                "resource_key": resource.resource_key,
            },
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return action


def _new_github_grant(
    db: Session,
    action: CaseAction,
    case: Case,
    github_params: dict[str, Any],
) -> CompanyResource:
    """Create the grant once GitHub confirmed its deploy key; the key id is
    filled in by _apply_verified_github_change."""
    details = dict((action.requested_data or {}).get("parameters") or {})
    details["github"] = {"repo": github_params["repo"]}
    resource = CompanyResource(
        person_id=case.subject_person_id,
        resource_type=action.resource_type,
        resource_key=(action.requested_data or {})["resource_key"],
        status=target_resource_state(action.action_type, action.resource_type),
        details_data=details,
        source_action_id=action.id,
        idempotency_key=action.idempotency_key,
    )
    db.add(resource)
    db.flush()
    record_audit_event(
        db,
        actor_type=AuditActorType.SYSTEM,
        event_type="RESOURCE_GRANTED_TEMPORARILY",
        entity_type="company_resource",
        entity_id=resource.id,
        after_data={"resource_key": resource.resource_key, "github": details["github"]},
        evidence_data={"action_id": str(action.id)},
        correlation_id=case.id,
    )
    return resource


def _apply_verified_github_change(
    resource: CompanyResource,
    action: CaseAction,
    verification: GitHubVerification,
) -> None:
    """Record on the resource what GitHub confirmed (never what n8n said)."""
    parameters = (action.requested_data or {}).get("parameters", {})
    details = dict(resource.details_data or {})
    github = dict(details.get("github") or {})

    if verification.new_key_id is not None:
        github["previous_key_id"] = github.get("key_id")
        github["key_id"] = verification.new_key_id
    elif action.action_type == ActionType.REVOKE and "key_id" in github:
        github["previous_key_id"] = github.get("key_id")
        github["key_id"] = None
    if action.action_type == ActionType.DOWNSCOPE:
        details["permission"] = "read"

    if action_moves_owner(action.action_type, parameters):
        details["previous_person_id"] = str(resource.person_id)
        resource.person_id = successor_from_parameters(parameters)

    applied_keys = dict(details.get("applied_keys") or {})
    applied_keys[action.idempotency_key] = action.action_type.value
    details["applied_keys"] = applied_keys
    details["github"] = github

    resource.details_data = details
    resource.status = target_resource_state(action.action_type, resource.resource_type)
    resource.source_action_id = action.id


def reconcile_applied_action(
    db: Session,
    action: CaseAction,
    case: Case,
) -> bool:
    if action.status not in {
        ActionState.DISPATCHED,
        ActionState.FAILED,
    }:
        return False

    resource = db.scalar(
        select(CompanyResource).where(
            or_(
                CompanyResource.idempotency_key
                == action.idempotency_key,
                CompanyResource.source_action_id == action.id,
            )
        )
    )

    if resource is None:
        return False

    action_data = action.requested_data or {}
    expected_key = action_data.get("resource_key")
    expected_person_id = _expected_person_id(action, case)
    expected_state = target_resource_state(
        action.action_type,
        action.resource_type,
    )

    if (
        resource.resource_key != expected_key
        or resource.resource_type != action.resource_type
        or resource.person_id != expected_person_id
        or resource.status != expected_state
    ):
        raise ExecutionStateConflictError(
            "An execution record exists, but it does not match "
            f"action {action.id}."
        )

    previous_status = action.status
    action.status = ActionState.VERIFIED
    action.error_message = None
    action.result_data = {
        "resource_id": str(resource.id),
        "resource_key": resource.resource_key,
        "resource_status": resource.status.value,
        "already_existed": True,
        "reconciled": True,
    }
    action.verification_data = {
        "verified": True,
        "resource_id": str(resource.id),
        "resource_key": resource.resource_key,
        "resource_type": resource.resource_type.value,
        "resource_status": resource.status.value,
        "person_id": str(resource.person_id),
        "source_action_id": str(resource.source_action_id),
        "reconciled": True,
    }

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="ACTION_RECONCILED_AND_VERIFIED",
            entity_type="case_action",
            entity_id=action.id,
            before_data={"status": previous_status.value},
            after_data={
                "status": action.status.value,
                "result": action.result_data,
                "verification_data": action.verification_data,
            },
            evidence_data={
                "resource_id": str(resource.id),
                "idempotency_key": action.idempotency_key,
            },
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return True


def _start_execution(
    db: Session,
    plan: CasePlan,
    case: Case,
    actions: list[CaseAction],
    *,
    is_resume: bool,
) -> None:
    previous_status = case.status
    case.status = CaseState.EXECUTING
    case.failure_reason = None
    event_type = (
        "CASE_EXECUTION_RESUMED"
        if is_resume
        else "CASE_EXECUTION_STARTED"
    )

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type=event_type,
            entity_type="case",
            entity_id=case.id,
            before_data={"status": previous_status.value},
            after_data={
                "status": case.status.value,
                "plan_id": str(plan.id),
            },
            evidence_data={
                "plan_revision": plan.revision,
                "action_count": len(actions),
            },
            correlation_id=case.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def _complete_case_if_verified(
    db: Session,
    plan: CasePlan,
    case: Case,
    actions: list[CaseAction],
) -> None:
    if not actions or any(
        action.status != ActionState.VERIFIED for action in actions
    ):
        raise ExecutionStateConflictError(
            "Case cannot be completed until every action is VERIFIED."
        )

    previous_status = case.status
    case.status = CaseState.COMPLETED
    case.failure_reason = None
    resolve_remediated_impact(db, case)

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="CASE_EXECUTION_COMPLETED",
            entity_type="case",
            entity_id=case.id,
            before_data={"status": previous_status.value},
            after_data={
                "status": case.status.value,
                "plan_id": str(plan.id),
            },
            evidence_data={
                "verified_action_ids": [
                    str(action.id) for action in actions
                ],
                "verified_action_count": len(actions),
            },
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(case)
    except Exception:
        db.rollback()
        raise


def _run_actions(
    db: Session,
    plan: CasePlan,
    case: Case,
    actions: list[CaseAction],
    *,
    is_resume: bool,
) -> list[CaseAction]:
    completed_actions: list[CaseAction] = []

    for action in actions:
        if action.status == ActionState.VERIFIED:
            completed_actions.append(action)
            continue

        if action.status == ActionState.SUCCEEDED:
            completed_actions.append(
                verify_action_resource(db, action, case)
            )
            continue

        if reconcile_applied_action(db, action, case):
            completed_actions.append(action)
            continue

        completed_actions.append(
            execute_single_action(db, action, case)
        )

    try:
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type=(
                "PLAN_ACTIONS_RESUMED_AND_VERIFIED"
                if is_resume
                else "PLAN_ACTIONS_VERIFIED"
            ),
            entity_type="case_plan",
            entity_id=plan.id,
            before_data=None,
            after_data={
                "case_status": case.status.value,
                "verified_actions": len(completed_actions),
            },
            evidence_data={
                "action_ids": [
                    str(action.id) for action in completed_actions
                ],
            },
            correlation_id=case.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return completed_actions


def execute_approved_plan(
    db: Session,
    plan_id: UUID,
) -> tuple[Case, list[CaseAction]]:
    plan, case, actions = get_execution_context(db, plan_id)
    _start_execution(
        db,
        plan,
        case,
        actions,
        is_resume=False,
    )
    completed_actions = _run_actions(
        db,
        plan,
        case,
        actions,
        is_resume=False,
    )
    _complete_case_if_verified(db, plan, case, completed_actions)
    return case, completed_actions


def retry_failed_plan(
    db: Session,
    plan_id: UUID,
) -> tuple[Case, list[CaseAction]]:
    plan, case, actions = get_retry_context(db, plan_id)
    _start_execution(
        db,
        plan,
        case,
        actions,
        is_resume=True,
    )
    completed_actions = _run_actions(
        db,
        plan,
        case,
        actions,
        is_resume=True,
    )
    _complete_case_if_verified(db, plan, case, completed_actions)
    return case, completed_actions
