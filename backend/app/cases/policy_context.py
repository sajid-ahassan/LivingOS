from app.enums import CaseType
from app.models import Case


from sqlalchemy.orm import Session

from app.cases.schemas import (
    CasePolicyContextResponse,
    PolicyEvidenceResponse,
)
from app.enums import CaseState
from app.rag.hybrid_retriever import (
    search_current_policies_hybrid,
)


BASE_POLICY_QUERIES = {
    CaseType.ONBOARDING: (
        "Employee onboarding requirements, account creation, "
        "system access, equipment assignment, training and approvals"
    ),
    CaseType.OFFBOARDING: (
        "Employee offboarding requirements, disable accounts, "
        "revoke access, return equipment, reassign work and handover"
    ),
}


OPTIONAL_REQUIREMENT_TERMS = {
    "requires_email": "email account",
    "requires_github": "GitHub access",
    "requires_laptop": "company laptop",
    "requires_training": "required employee training",
}



class PolicyContextStateError(ValueError):
    pass


class PolicyEvidenceNotFoundError(ValueError):
    pass


def retrieve_case_policy_context(
    db: Session,
    case: Case,
    *,
    top_k: int = 5,
) -> CasePolicyContextResponse:
    if case.status != CaseState.PLANNING:
        raise PolicyContextStateError(
            f"Policy retrieval requires PLANNING state, "
            f"but the case is {case.status.value}."
        )

    search_query = build_case_policy_query(case)

    results = search_current_policies_hybrid(
        db,
        query=search_query,
        top_k=top_k,
        candidate_k=max(10, top_k),
    )

    if not results:
        raise PolicyEvidenceNotFoundError(
            "No current policy evidence was found."
        )

    evidence = [
        PolicyEvidenceResponse(
            evidence_id=result.evidence_id,
            policy_code=result.policy_code,
            version_number=result.version_number,
            text=result.text,
            score=result.score,
        )
        for result in results
    ]

    return CasePolicyContextResponse(
        case_id=case.id,
        search_query=search_query,
        evidence=evidence,
    )



def build_case_policy_query(
    case: Case,
) -> str:
    facts = case.case_facts or {}
    query_parts = [BASE_POLICY_QUERIES[case.case_type]]

    department = facts.get("department")

    if department:
        query_parts.append(f"Department: {department}")

    job_title = facts.get("job_title")

    if job_title:
        query_parts.append(f"Job title: {job_title}")

    for fact_name, search_term in OPTIONAL_REQUIREMENT_TERMS.items():
        if facts.get(fact_name) is True:
            query_parts.append(search_term)

    return ". ".join(query_parts)