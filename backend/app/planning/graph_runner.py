from __future__ import annotations

import json
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cases.policy_context import retrieve_case_policy_context
from app.cases.schemas import CasePolicyContextResponse
from app.config import get_settings
from app.graphs.onboarding import build_onboarding_graph
from app.models import Case, CompanyResource, Person
from app.planning.prompt import PLANNING_PROMPT, format_policy_evidence
from app.planning.schemas import GeneratedCasePlan
from app.planning.validation import (
    ALLOWED_ACTIONS,
    GeneratedPlanValidationError,
    validate_generated_plan,
)


REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are repairing a LivingOps onboarding plan that failed deterministic validation.

Return only a corrected GeneratedCasePlan structured object.

Rules:
- Keep the same case facts and policy evidence.
- Fix only the listed validation errors.
- Do not invent resources, policy rules, evidence IDs, or approvals.
- Every action must cite evidence IDs from POLICY_EVIDENCE.
- Respect ALLOWED_ACTIONS.
- Do not broaden access beyond the supplied policy evidence.
""".strip(),
        ),
        (
            "human",
            """
CASE_TYPE:
{case_type}

ALLOWED_ACTIONS:
{allowed_actions}

SUBJECT_CONTEXT:
{subject_context}

CASE_FACTS:
{case_facts}

EXISTING_RESOURCES:
{existing_resources}

POLICY_EVIDENCE:
{policy_evidence}

FAILED_DRAFT:
{failed_draft}

VALIDATION_ERRORS:
{validation_errors}
""".strip(),
        ),
    ]
)


def _load_subject_and_resources(
    db: Session,
    case: Case,
) -> tuple[Person, list[CompanyResource]]:
    subject = db.get(Person, case.subject_person_id)
    if subject is None:
        raise ValueError("The case subject no longer exists.")

    resources = list(
        db.scalars(
            select(CompanyResource).where(
                CompanyResource.person_id == subject.id
            )
        )
    )
    return subject, resources


def _subject_context(subject: Person) -> dict:
    return {
        "id": subject.id,
        "name": subject.name,
        "email": subject.email,
        "department": subject.department,
        "job_title": subject.job_title,
        "employment_status": subject.employment_status,
        "manager_id": subject.manager_id,
    }


def _resource_context(
    resources: list[CompanyResource],
) -> list[dict]:
    return [
        {
            "resource_type": resource.resource_type,
            "resource_key": resource.resource_key,
            "status": resource.status,
            "details_data": resource.details_data,
        }
        for resource in resources
    ]


def _model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def _planning_inputs(
    case: Case,
    subject: Person,
    resources: list[CompanyResource],
    policy_context: CasePolicyContextResponse,
) -> dict:
    return {
        "case_type": case.case_type.value,
        "allowed_actions": ", ".join(
            action.value
            for action in sorted(
                ALLOWED_ACTIONS[case.case_type],
                key=lambda item: item.value,
            )
        ),
        "subject_context": json.dumps(
            jsonable_encoder(_subject_context(subject)),
            indent=2,
        ),
        "case_facts": json.dumps(
            jsonable_encoder(case.case_facts),
            indent=2,
        ),
        "existing_resources": json.dumps(
            jsonable_encoder(_resource_context(resources)),
            indent=2,
        ),
        "policy_evidence": format_policy_evidence(policy_context),
    }


def generate_case_plan_via_graph(
    db: Session,
    case: Case,
    policy_context: CasePolicyContextResponse | None = None,
) -> GeneratedCasePlan:
    """
    Run onboarding planning through LangGraph while keeping all PostgreSQL
    persistence in the existing planning service.

    The graph performs:
    load_case -> retrieve_context -> generate_plan -> validate_plan
    -> one repair if needed -> validate_plan -> end/human review.
    """
    if policy_context is None:
        policy_context = retrieve_case_policy_context(db, case)

    subject, resources = _load_subject_and_resources(db, case)

    def load_case_fn(case_id: str) -> dict:
        if str(case.id) != str(case_id):
            raise ValueError("Graph case_id does not match the loaded case.")

        return {
            "case_id": str(case.id),
            "case_type": case.case_type.value,
            "case_facts": jsonable_encoder(case.case_facts),
            "subject": jsonable_encoder(_subject_context(subject)),
        }

    def retrieve_context_fn(_facts: dict) -> dict:
        return {
            "policy_context": policy_context,
            "resources": resources,
        }

    def generate_plan_fn(
        _facts: dict,
        _retrieval: dict,
    ) -> dict:
        structured_model = _model().with_structured_output(
            GeneratedCasePlan,
            method="function_calling",
        )
        chain = PLANNING_PROMPT | structured_model

        result = chain.invoke(
            _planning_inputs(
                case,
                subject,
                resources,
                policy_context,
            )
        )

        return GeneratedCasePlan.model_validate(
            result
        ).model_dump(mode="json")

    def validate_plan_fn(
        draft: dict,
        _retrieval: dict,
    ) -> list[str]:
        try:
            plan = GeneratedCasePlan.model_validate(draft)
            validate_generated_plan(
                plan,
                case=case,
                policy_context=policy_context,
                resources=resources,
            )
            return []
        except (GeneratedPlanValidationError, ValueError) as exc:
            return [str(exc)]

    def repair_plan_fn(
        draft: dict,
        errors: list[str],
        _retrieval: dict,
    ) -> dict:
        structured_model = _model().with_structured_output(
            GeneratedCasePlan,
            method="function_calling",
        )
        chain = REPAIR_PROMPT | structured_model

        inputs = _planning_inputs(
            case,
            subject,
            resources,
            policy_context,
        )
        inputs.update(
            {
                "failed_draft": json.dumps(
                    jsonable_encoder(draft),
                    indent=2,
                ),
                "validation_errors": json.dumps(
                    errors,
                    indent=2,
                ),
            }
        )

        repaired = chain.invoke(inputs)

        return GeneratedCasePlan.model_validate(
            repaired
        ).model_dump(mode="json")

    graph = build_onboarding_graph(
        load_case_fn=load_case_fn,
        retrieve_context_fn=retrieve_context_fn,
        generate_plan_fn=generate_plan_fn,
        validate_plan_fn=validate_plan_fn,
        repair_plan_fn=repair_plan_fn,
    )

    result = graph.invoke(
        {
            "case_id": str(case.id),
            "correlation_id": str(case.id),
            "repair_count": 0,
        }
    )

    terminal_state = result.get("terminal_state")

    if terminal_state == "NEEDS_HUMAN_REVIEW":
        errors = result.get("validation_errors") or []
        raise GeneratedPlanValidationError(
            "Onboarding LangGraph could not produce a valid plan "
            f"after one repair attempt. Errors: {'; '.join(errors)}"
        )

    final_output = result.get("final_output")
    if not final_output:
        raise GeneratedPlanValidationError(
            "Onboarding LangGraph returned no final plan."
        )

    return GeneratedCasePlan.model_validate(final_output)
