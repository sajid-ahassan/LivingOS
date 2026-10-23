from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.policy_context import retrieve_case_policy_context
from app.cases.schemas import CasePolicyContextResponse
from app.cases.service import CaseNotFoundError
from app.enums import (
    ActionState,
    AuditActorType,
    CaseState,
    PlanState,
    PolicyLinkSubjectType,
)
from app.models import (
    Case,
    CaseAction,
    CasePlan,
    PolicyLink,
    PolicyVersion,
)
from app.planning.graph_runner import generate_case_plan_via_graph
from app.planning.schemas import GeneratedCasePlan, PlannedAction


class PolicyVersionNotFoundError(ValueError):
    pass


class CasePlanningError(ValueError):
    pass



def get_next_plan_revision(
    db: Session,
    case_id: UUID,
) -> int:
    latest_revision = db.scalar(
        select(func.max(CasePlan.revision)).where(
            CasePlan.case_id == case_id
        )
    )

    return (latest_revision or 0) + 1


def build_case_action(
    *,
    case: Case,
    plan: CasePlan,
    action: PlannedAction,
) -> CaseAction:
    return CaseAction(
        case_id=case.id,
        plan_id=plan.id,
        action_type=action.action_type,
        resource_type=action.resource_type,
        requested_data={
            "sequence": action.sequence,
            "resource_key": action.resource_key,
            "parameters": jsonable_encoder(
                action.requested_data
            ),
            "reason": action.reason,
            "evidence_ids": action.evidence_ids,
        },
        status=ActionState.PENDING,
        idempotency_key=(
            f"case:{case.id}:"
            f"plan:{plan.revision}:"
            f"action:{action.sequence}"
        ),
    )




def build_policy_links(
    db: Session,
    plan: CasePlan,
    generated_plan: GeneratedCasePlan,
    policy_context: CasePolicyContextResponse,
) -> list[PolicyLink]:
    evidence_lookup = {
        item.evidence_id: item
        for item in policy_context.evidence
    }

    used_evidence_ids = {
        evidence_id
        for action in generated_plan.actions
        for evidence_id in action.evidence_ids
    }

    evidence_by_policy: dict[tuple[str, int], set[str]] = {}

    for evidence_id in used_evidence_ids:
        evidence = evidence_lookup[evidence_id]
        policy_key = (
            evidence.policy_code,
            evidence.version_number,
        )

        evidence_by_policy.setdefault(
            policy_key,
            set(),
        ).add(evidence_id)

    links: list[PolicyLink] = []

    for (
        policy_code,
        version_number,
    ), evidence_ids in evidence_by_policy.items():
        policy_version = db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.policy_code == policy_code,
                PolicyVersion.version_number == version_number,
            )
        )

        if policy_version is None:
            raise PolicyVersionNotFoundError(
                f"Policy version not found: "
                f"{policy_code} V{version_number}"
            )

        links.append(
            PolicyLink(
                policy_version_id=policy_version.id,
                subject_type=PolicyLinkSubjectType.PLAN,
                subject_id=plan.id,
                use_reason="AI case planning",
                evidence_ids=sorted(evidence_ids),
            )
        )

    return links





def save_generated_plan(
    db: Session,
    case: Case,
    generated_plan: GeneratedCasePlan,
    policy_context: CasePolicyContextResponse,
) -> CasePlan:
    revision = get_next_plan_revision(
        db,
        case.id,
    )

    plan = CasePlan(
        case_id=case.id,
        revision=revision,
        status=PlanState.DRAFT,
        summary=generated_plan.summary,
        plan_data=jsonable_encoder(
            generated_plan.model_dump()
        ),
    )

    db.add(plan)

    # Generate plan.id before creating related records.
    db.flush()

    actions = [
        build_case_action(
            case=case,
            plan=plan,
            action=action,
        )
        for action in generated_plan.actions
    ]

    policy_links = build_policy_links(
        db,
        plan,
        generated_plan,
        policy_context,
    )

    db.add_all(actions)
    db.add_all(policy_links)

    return plan



def create_case_plan(
    db: Session,
    case_id: UUID,
) -> CasePlan:
    case = db.get(Case, case_id)

    if case is None:
        raise CaseNotFoundError(
            f"Case does not exist: {case_id}"
        )

    if case.status != CaseState.PLANNING:
        raise CasePlanningError(
            f"Case must be in PLANNING state. "
            f"Current state: {case.status.value}"
        )

    try:
        policy_context = retrieve_case_policy_context(
            db,
            case,
        )

        generated_plan = generate_case_plan_via_graph(
            db,
            case,
            policy_context,
        )

        plan = save_generated_plan(
            db,
            case,
            generated_plan,
            policy_context,
        )

        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.LLM,
            event_type="CASE_PLAN_GENERATED",
            entity_type="case_plan",
            entity_id=plan.id,
            before_data=None,
            after_data={
                "case_id": str(case.id),
                "revision": plan.revision,
                "status": plan.status.value,
                "summary": plan.summary,
                "action_count": len(
                    generated_plan.actions
                ),
            },
            evidence_data={
                "evidence_ids": sorted({
                    evidence_id
                    for action in generated_plan.actions
                    for evidence_id in action.evidence_ids
                }),
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(plan)

    except Exception:
        db.rollback()
        raise

    return plan
