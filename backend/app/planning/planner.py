import json

from fastapi.encoders import jsonable_encoder
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cases.schemas import CasePolicyContextResponse
from app.config import get_settings
from app.models import Case, CompanyResource, Person
from app.planning.prompt import (
    PLANNING_PROMPT,
    format_policy_evidence,
)
from app.planning.schemas import GeneratedCasePlan

from app.planning.validation import (
    ALLOWED_ACTIONS,
    validate_generated_plan,
)

class PlanningContextError(ValueError):
    pass


def generate_case_plan(
    db: Session,
    case: Case,
    policy_context: CasePolicyContextResponse,
) -> GeneratedCasePlan:
    subject = db.get(Person, case.subject_person_id)

    if subject is None:
        raise PlanningContextError(
            "The case subject no longer exists."
        )

    resources = list(
        db.scalars(
            select(CompanyResource).where(
                CompanyResource.person_id == subject.id
            )
        )
    )

    subject_context = {
        "id": subject.id,
        "name": subject.name,
        "email": subject.email,
        "department": subject.department,
        "job_title": subject.job_title,
        "employment_status": subject.employment_status,
        "manager_id": subject.manager_id,
    }

    resource_context = [
        {
            "resource_type": resource.resource_type,
            "resource_key": resource.resource_key,
            "status": resource.status,
            "details_data": resource.details_data,
        }
        for resource in resources
    ]

    settings = get_settings()

    model = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    structured_model = model.with_structured_output(
        GeneratedCasePlan,
        method="function_calling",
    )

    chain = PLANNING_PROMPT | structured_model

    result = chain.invoke(
        {
            "case_type": case.case_type.value,
            "allowed_actions": ", ".join(
                action.value
                for action in sorted(
                    ALLOWED_ACTIONS[case.case_type],
                    key=lambda item: item.value,
                )
            ),
            "subject_context": json.dumps(
                jsonable_encoder(subject_context),
                indent=2,
            ),
            "case_facts": json.dumps(
                jsonable_encoder(case.case_facts),
                indent=2,
            ),
            "existing_resources": json.dumps(
                jsonable_encoder(resource_context),
                indent=2,
            ),
            "policy_evidence": format_policy_evidence(
                policy_context
            ),
        }
    )

    plan = GeneratedCasePlan.model_validate(result)

    validate_generated_plan(
        plan,
        case=case,
        policy_context=policy_context,
        resources=resources,
    )

    return plan