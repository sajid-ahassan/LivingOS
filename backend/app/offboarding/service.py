import json
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.policy_context import retrieve_case_policy_context
from app.cases.service import CaseNotFoundError
from app.config import get_settings
from app.enums import (
    ActionType,
    AuditActorType,
    CaseState,
    CaseType,
    PlanState,
    ResourceType,
)
from app.models import Case, CasePlan, CompanyResource, Person
from app.offboarding.prompt import OFFBOARDING_PROMPT
from app.offboarding.rules import required_action_for_resource, safe_resource_metadata
from app.offboarding.graph_runner import generate_offboarding_plan_via_graph
from app.offboarding.schemas import OffboardingPlan
from app.planning.prompt import format_policy_evidence
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


def validate_offboarding_plan(
    db: Session,
    case: Case,
    plan: OffboardingPlan,
    resources: list[CompanyResource],
    allowed_evidence_ids: set[str],
) -> None:
    errors: list[str] = []
    actions = _flatten_actions(plan)

    actual_sequences = [item.sequence for item in actions]
    expected_sequences = list(range(1, len(actions) + 1))
    if actual_sequences != expected_sequences:
        errors.append("Executable action sequence must start at 1 and be consecutive.")

    by_key = {resource.resource_key: resource for resource in resources}
    planned_by_key: dict[str, list] = {}

    for action in actions:
        planned_by_key.setdefault(action.resource_key, []).append(action)

        resource = by_key.get(action.resource_key)
        if resource is None:
            errors.append(f"Unknown resource key: {action.resource_key}.")
            continue

        if action.resource_type != resource.resource_type:
            errors.append(f"Wrong resource type for {action.resource_key}.")

        invalid_evidence = set(action.evidence_ids) - allowed_evidence_ids
        if invalid_evidence:
            errors.append(
                f"Action for {action.resource_key} cites unavailable evidence: "
                f"{sorted(invalid_evidence)}."
            )

        required_action = required_action_for_resource(resource)
        if required_action is None:
            errors.append(
                f"Resource {action.resource_key} does not require an offboarding action."
            )
        elif action.action_type != required_action:
            errors.append(
                f"Resource {action.resource_key} requires {required_action.value}, "
                f"not {action.action_type.value}."
            )

        if action.action_type == ActionType.REASSIGN:
            successor_value = action.requested_data.get("successor_person_id")
            if not successor_value:
                errors.append(
                    f"REASSIGN for {action.resource_key} requires successor_person_id."
                )
            else:
                try:
                    successor_id = UUID(str(successor_value))
                except (TypeError, ValueError):
                    errors.append(
                        f"Invalid successor_person_id for {action.resource_key}."
                    )
                else:
                    successor = db.get(Person, successor_id)
                    if successor is None:
                        errors.append(
                            f"Successor does not exist for {action.resource_key}."
                        )
                    elif successor.id == case.subject_person_id:
                        errors.append("Departing employee cannot be their own successor.")

        if (
            action.action_type == ActionType.REQUEST_RETURN
            and not action.requested_data.get("due_date")
        ):
            errors.append(
                f"REQUEST_RETURN for {action.resource_key} requires due_date."
            )

    for resource in resources:
        required_action = required_action_for_resource(resource)
        if required_action is None:
            continue

        matching = planned_by_key.get(resource.resource_key, [])
        if len(matching) != 1:
            errors.append(
                f"Resource {resource.resource_key} requires exactly one "
                f"{required_action.value} action."
            )

    work_or_docs = [
        resource
        for resource in resources
        if resource.resource_type
        in {ResourceType.WORK_ITEM, ResourceType.KNOWLEDGE_DOCUMENT}
        and required_action_for_resource(resource) == ActionType.REASSIGN
    ]
    if work_or_docs and len(plan.targeted_questions) < 2:
        errors.append(
            "Offboarding with open work or documents requires at least two targeted handover questions."
        )

    for question in plan.targeted_questions:
        lowered = question.lower()
        forbidden = ("password", "private message", "personal file", "secret key")
        if any(term in lowered for term in forbidden):
            errors.append("A targeted question crosses the privacy boundary.")

    if errors:
        raise OffboardingValidationError(" ".join(errors))


def _generate_offboarding_plan(
    db: Session,
    case: Case,
    resources: list[CompanyResource],
):
    subject = db.get(Person, case.subject_person_id)
    if subject is None:
        raise OffboardingPlanningError("The departing employee no longer exists.")

    policy_context = retrieve_case_policy_context(db, case)

    subject_context = {
        "id": str(subject.id),
        "name": subject.name,
        "department": subject.department,
        "job_title": subject.job_title,
        "manager_id": str(subject.manager_id) if subject.manager_id else None,
    }

    case_facts = dict(case.case_facts or {})
    if not case_facts.get("successor_person_id") and case_facts.get("manager_id"):
        case_facts["successor_person_id"] = case_facts["manager_id"]
        case_facts["successor_source"] = "manager_id_fallback"

    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    structured_model = model.with_structured_output(
        OffboardingPlan,
        method="function_calling",
    )
    chain = OFFBOARDING_PROMPT | structured_model

    result = chain.invoke(
        {
            "case_facts": json.dumps(jsonable_encoder(case_facts), indent=2),
            "subject_context": json.dumps(jsonable_encoder(subject_context), indent=2),
            "resource_inventory": json.dumps(
                [safe_resource_metadata(resource) for resource in resources],
                indent=2,
            ),
            "policy_evidence": format_policy_evidence(policy_context),
        }
    )

    plan = OffboardingPlan.model_validate(result)

    for sequence, action in enumerate(_flatten_actions(plan), start=1):
        action.sequence = sequence

    validate_offboarding_plan(
        db,
        case,
        plan,
        resources,
        {item.evidence_id for item in policy_context.evidence},
    )
    return plan, policy_context


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
