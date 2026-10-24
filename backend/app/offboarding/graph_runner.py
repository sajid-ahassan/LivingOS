from __future__ import annotations

import json
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.cases.policy_context import retrieve_case_policy_context
from app.config import get_settings
from app.enums import ActionType
from app.graphs.offboarding import build_offboarding_graph
from app.models import Case, CompanyResource, Person
from app.offboarding.prompt import OFFBOARDING_PROMPT
from app.offboarding.rules import required_action_for_resource, safe_resource_metadata
from app.offboarding.schemas import OffboardingPlan
from app.planning.prompt import format_policy_evidence


class OffboardingPlanningError(ValueError):
    pass


def _flatten_actions(plan: OffboardingPlan):
    return [
        *plan.revocations,
        *plan.asset_returns,
        *plan.reassignments,
    ]


QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are the LivingOps offboarding handover-question planner.

Generate only targeted, work-related handover questions.
Use only the supplied case facts, approved resource metadata, policy evidence,
and already-generated offboarding plan.

Do not ask for passwords, secrets, private messages, personal files, or
unrelated personal information.

Return a JSON object with exactly one key:
{"questions": ["...", "..."]}
""".strip(),
        ),
        (
            "human",
            """
CASE_FACTS:
{case_facts}

RESOURCE_INVENTORY:
{resource_inventory}

POLICY_EVIDENCE:
{policy_evidence}

OFFBOARDING_PLAN:
{offboarding_plan}
""".strip(),
        ),
    ]
)


REPAIR_PLAN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Repair the supplied LivingOps offboarding plan.

Return only a corrected OffboardingPlan structured object.
Fix only the listed deterministic validation errors.
Use only supplied resources and evidence IDs.
Do not invent company resources, successor IDs, policy rules, or approvals.
Do not ask for or expose secrets/private data.
""".strip(),
        ),
        (
            "human",
            """
CASE_FACTS:
{case_facts}

RESOURCE_INVENTORY:
{resource_inventory}

POLICY_EVIDENCE:
{policy_evidence}

FAILED_PLAN:
{failed_plan}

VALIDATION_ERRORS:
{validation_errors}
""".strip(),
        ),
    ]
)


REPAIR_QUESTIONS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Repair the targeted handover questions for a LivingOps offboarding plan.

Return JSON with exactly:
{"questions": ["...", "..."]}

Fix only the supplied validation errors.
Questions must remain work-related and must never request passwords, secrets,
private messages, personal files, secret keys, or unrelated personal data.
""".strip(),
        ),
        (
            "human",
            """
CASE_FACTS:
{case_facts}

RESOURCE_INVENTORY:
{resource_inventory}

POLICY_EVIDENCE:
{policy_evidence}

CURRENT_QUESTIONS:
{current_questions}

VALIDATION_ERRORS:
{validation_errors}
""".strip(),
        ),
    ]
)


def _model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def _subject_context(subject: Person) -> dict:
    return {
        "id": str(subject.id),
        "name": subject.name,
        "department": subject.department,
        "job_title": subject.job_title,
        "manager_id": str(subject.manager_id) if subject.manager_id else None,
    }


def _normalised_case_facts(case: Case) -> dict:
    case_facts = dict(case.case_facts or {})
    if not case_facts.get("successor_person_id") and case_facts.get("manager_id"):
        case_facts["successor_person_id"] = case_facts["manager_id"]
        case_facts["successor_source"] = "manager_id_fallback"
    return case_facts


def _base_inputs(
    case: Case,
    subject: Person,
    resources: list[CompanyResource],
    policy_context,
) -> dict:
    return {
        "case_facts": json.dumps(
            jsonable_encoder(_normalised_case_facts(case)),
            indent=2,
        ),
        "subject_context": json.dumps(
            jsonable_encoder(_subject_context(subject)),
            indent=2,
        ),
        "resource_inventory": json.dumps(
            [safe_resource_metadata(resource) for resource in resources],
            indent=2,
        ),
        "policy_evidence": format_policy_evidence(policy_context),
    }


def _validate_execution_plan(
    db: Session,
    case: Case,
    plan: OffboardingPlan,
    resources: list[CompanyResource],
    allowed_evidence_ids: set[str],
) -> list[str]:
    """
    Validate the executable offboarding actions only.
    Targeted questions are validated at the graph's second boundary.
    """
    errors: list[str] = []
    actions = _flatten_actions(plan)

    actual_sequences = [item.sequence for item in actions]
    expected_sequences = list(range(1, len(actions) + 1))
    if actual_sequences != expected_sequences:
        errors.append(
            "Executable action sequence must start at 1 and be consecutive."
        )

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
                        errors.append(
                            "Departing employee cannot be their own successor."
                        )

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

    return errors


def _validate_questions(
    questions: list[str],
    resources: list[CompanyResource],
) -> list[str]:
    errors: list[str] = []

    work_or_docs = [
        resource
        for resource in resources
        if required_action_for_resource(resource) == ActionType.REASSIGN
    ]

    if work_or_docs and len(questions) < 2:
        errors.append(
            "Offboarding with open work or documents requires at least "
            "two targeted handover questions."
        )

    if len(questions) > 12:
        errors.append("At most 12 targeted handover questions are allowed.")

    forbidden = (
        "password",
        "private message",
        "personal file",
        "secret key",
    )

    for question in questions:
        lowered = question.lower()
        if any(term in lowered for term in forbidden):
            errors.append(
                "A targeted question crosses the privacy boundary."
            )

    return errors


def generate_offboarding_plan_via_graph(
    db: Session,
    case: Case,
    resources: list[CompanyResource],
) -> tuple[OffboardingPlan, object]:
    subject = db.get(Person, case.subject_person_id)
    if subject is None:
        raise OffboardingPlanningError(
            "The departing employee no longer exists."
        )

    policy_context = retrieve_case_policy_context(db, case)
    allowed_evidence_ids = {
        item.evidence_id for item in policy_context.evidence
    }

    def load_case_fn(case_id: str) -> dict:
        if str(case.id) != str(case_id):
            raise OffboardingPlanningError(
                "Graph case_id does not match the loaded case."
            )
        return {
            "case_id": str(case.id),
            "case_facts": jsonable_encoder(
                _normalised_case_facts(case)
            ),
            "subject": jsonable_encoder(
                _subject_context(subject)
            ),
        }

    def inventory_resources_fn(_facts: dict) -> list[dict]:
        return [
            safe_resource_metadata(resource)
            for resource in resources
        ]

    def retrieve_context_fn(
        _facts: dict,
        _resource_metadata: list[dict],
    ) -> dict:
        return {
            "policy_context": policy_context,
            "allowed_evidence_ids": sorted(allowed_evidence_ids),
        }

    def generate_plan_fn(
        _facts: dict,
        _resource_metadata: list[dict],
        _retrieval: dict,
    ) -> dict:
        structured_model = _model().with_structured_output(
            OffboardingPlan,
            method="function_calling",
        )
        chain = OFFBOARDING_PROMPT | structured_model

        result = chain.invoke(
            _base_inputs(
                case,
                subject,
                resources,
                policy_context,
            )
        )

        plan = OffboardingPlan.model_validate(result)

        # Questions have their own graph node, so ignore any questions the
        # original prompt happened to return here.
        plan.targeted_questions = []

        for sequence, action in enumerate(
            _flatten_actions(plan),
            start=1,
        ):
            action.sequence = sequence

        return plan.model_dump(mode="json")

    def validate_plan_fn(
        draft: dict,
        _resource_metadata: list[dict],
        _retrieval: dict,
    ) -> list[str]:
        plan = OffboardingPlan.model_validate(draft)
        return _validate_execution_plan(
            db,
            case,
            plan,
            resources,
            allowed_evidence_ids,
        )

    def generate_questions_fn(
        _facts: dict,
        _resource_metadata: list[dict],
        _retrieval: dict,
        draft: dict,
    ) -> list[str]:
        chain = QUESTION_PROMPT | _model()
        response = chain.invoke(
            {
                **_base_inputs(
                    case,
                    subject,
                    resources,
                    policy_context,
                ),
                "offboarding_plan": json.dumps(
                    jsonable_encoder(draft),
                    indent=2,
                ),
            }
        )

        content = response.content
        if isinstance(content, list):
            content = "".join(
                str(item) for item in content
            )

        payload = json.loads(str(content))
        questions = payload.get("questions", [])
        if not isinstance(questions, list):
            raise OffboardingPlanningError(
                "Question generator returned an invalid questions payload."
            )

        return [str(item).strip() for item in questions if str(item).strip()]

    def validate_questions_fn(
        questions: list[str],
        _facts: dict,
        _resource_metadata: list[dict],
    ) -> list[str]:
        return _validate_questions(
            questions,
            resources,
        )

    def repair_plan_fn(
        draft: dict,
        errors: list[str],
        _retrieval: dict,
    ) -> dict:
        structured_model = _model().with_structured_output(
            OffboardingPlan,
            method="function_calling",
        )
        chain = REPAIR_PLAN_PROMPT | structured_model

        result = chain.invoke(
            {
                **_base_inputs(
                    case,
                    subject,
                    resources,
                    policy_context,
                ),
                "failed_plan": json.dumps(
                    jsonable_encoder(draft),
                    indent=2,
                ),
                "validation_errors": json.dumps(
                    errors,
                    indent=2,
                ),
            }
        )

        repaired = OffboardingPlan.model_validate(result)
        repaired.targeted_questions = []

        for sequence, action in enumerate(
            _flatten_actions(repaired),
            start=1,
        ):
            action.sequence = sequence

        return repaired.model_dump(mode="json")

    def repair_questions_fn(
        current: dict,
        errors: list[str],
        _retrieval: dict,
    ) -> dict:
        chain = REPAIR_QUESTIONS_PROMPT | _model()
        response = chain.invoke(
            {
                **_base_inputs(
                    case,
                    subject,
                    resources,
                    policy_context,
                ),
                "current_questions": json.dumps(
                    current.get("questions", []),
                    indent=2,
                ),
                "validation_errors": json.dumps(
                    errors,
                    indent=2,
                ),
            }
        )

        content = response.content
        if isinstance(content, list):
            content = "".join(
                str(item) for item in content
            )

        payload = json.loads(str(content))
        return {
            "questions": [
                str(item).strip()
                for item in payload.get("questions", [])
                if str(item).strip()
            ]
        }

    graph = build_offboarding_graph(
        load_case_fn=load_case_fn,
        inventory_resources_fn=inventory_resources_fn,
        retrieve_context_fn=retrieve_context_fn,
        generate_plan_fn=generate_plan_fn,
        validate_plan_fn=validate_plan_fn,
        generate_questions_fn=generate_questions_fn,
        validate_questions_fn=validate_questions_fn,
        repair_plan_fn=repair_plan_fn,
        repair_questions_fn=repair_questions_fn,
    )

    result = graph.invoke(
        {
            "case_id": str(case.id),
            "correlation_id": str(case.id),
            "repair_count": 0,
        }
    )

    if result.get("terminal_state") == "NEEDS_HUMAN_REVIEW":
        errors = (
            result.get("question_errors")
            or result.get("validation_errors")
            or []
        )
        raise OffboardingPlanningError(
            "Offboarding LangGraph could not produce a valid plan "
            f"after one repair attempt. Errors: {'; '.join(errors)}"
        )

    final_output = result.get("final_output")
    if not final_output:
        raise OffboardingPlanningError(
            "Offboarding LangGraph returned no final plan."
        )

    plan = OffboardingPlan.model_validate(final_output)

    # Final deterministic safety check using the existing full validator
    # remains in the service after this function returns.
    return plan, policy_context
