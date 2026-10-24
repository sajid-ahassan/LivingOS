from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.service import CaseNotFoundError
from app.enums import (
    AuditActorType,
    CaseState,
    CaseType,
    PlanState,
)
from app.models import Case, CasePlan, CompanyResource
from app.offboarding.graph_runner import generate_offboarding_plan_via_graph
from app.offboarding.schemas import OffboardingPlan
from app.planning.schemas import GeneratedCasePlan
from app.planning.service import (
    build_case_action,
    build_policy_links,
    get_next_plan_revision,
)


class OffboardingPlanningError(ValueError):
    pass


class OffboardingValidationError(ValueError):
    pass


def get_offboarding_inventory(
    db: Session,
    case_id: UUID,
) -> tuple[Case, list[CompanyResource]]:
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case does not exist: {case_id}")
    if case.case_type != CaseType.OFFBOARDING:
        raise OffboardingPlanningError(
            "Resource inventory is available only for OFFBOARDING cases."
        )
    return case, inventory_offboarding_resources(db, case)


def inventory_offboarding_resources(
    db: Session,
    case: Case,
) -> list[CompanyResource]:
    return list(
        db.scalars(
            select(CompanyResource)
            .where(CompanyResource.person_id == case.subject_person_id)
            .order_by(CompanyResource.resource_type, CompanyResource.resource_key)
        )
    )


def _flatten_actions(plan: OffboardingPlan):
    return [
        *plan.revocations,
        *plan.asset_returns,
        *plan.reassignments,
    ]


def create_offboarding_plan(db: Session, case_id: UUID) -> CasePlan:
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case does not exist: {case_id}")

    if case.case_type != CaseType.OFFBOARDING:
        raise OffboardingPlanningError("This endpoint only accepts OFFBOARDING cases.")

    if case.status != CaseState.PLANNING:
        raise OffboardingPlanningError(
            f"Case must be in PLANNING state. Current state: {case.status.value}"
        )

    resources = inventory_offboarding_resources(db, case)
    if not resources:
        raise OffboardingPlanningError(
            "No company resources were found for the departing employee."
        )

    try:
        generated, policy_context = generate_offboarding_plan_via_graph(
            db,
            case,
            resources,
        )
        actions = _flatten_actions(generated)

        revision = get_next_plan_revision(db, case.id)
        plan = CasePlan(
            case_id=case.id,
            revision=revision,
            status=PlanState.DRAFT,
            summary=generated.summary,
            plan_data=jsonable_encoder(generated.model_dump()),
        )
        db.add(plan)
        db.flush()

        action_records = [
            build_case_action(case=case, plan=plan, action=action)
            for action in actions
        ]

        adapter = GeneratedCasePlan(
            summary=generated.summary,
            actions=actions,
            warnings=(
                ["Offboarding plan requires human review."]
                if generated.needs_human_review
                else []
            ),
        )
        policy_links = build_policy_links(db, plan, adapter, policy_context)

        db.add_all(action_records)
        db.add_all(policy_links)
        db.flush()

        record_audit_event(
            db,
            actor_type=AuditActorType.LLM,
            event_type="OFFBOARDING_PLAN_GENERATED",
            entity_type="case_plan",
            entity_id=plan.id,
            before_data=None,
            after_data={
                "case_id": str(case.id),
                "revision": plan.revision,
                "status": plan.status.value,
                "action_count": len(action_records),
                "targeted_question_count": len(generated.targeted_questions),
                "handover_topic_count": len(generated.handover_topics),
                "needs_human_review": generated.needs_human_review,
            },
            evidence_data={
                "resource_keys": [resource.resource_key for resource in resources],
                "evidence_ids": sorted({
                    evidence_id
                    for action in actions
                    for evidence_id in action.evidence_ids
                }),
            },
            correlation_id=case.id,
        )

        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise
