from app.enums import CaseType
from app.models import Case


REQUIRED_CASE_FACTS = {
    CaseType.ONBOARDING: {
        "start_date",
        "department",
        "job_title",
        "manager_id",
    },
    CaseType.OFFBOARDING: {
        "last_working_day",
        "manager_id",
    },
    CaseType.ACCESS_REQUEST: set(),
}


def find_missing_case_facts(
    case: Case,
) -> list[str]:
    required_fields = REQUIRED_CASE_FACTS[case.case_type]
    case_facts = case.case_facts or {}

    return sorted(
        field
        for field in required_fields
        if field not in case_facts
        or case_facts[field] is None
        or case_facts[field] == ""
    )