from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.cases.policy_context import PolicyEvidenceNotFoundError, PolicyContextStateError
from app.cases.service import CaseNotFoundError
from app.database import get_db
from app.offboarding.schemas import (
    OffboardingPlanResponse,
    OffboardingResourceInventoryItem,
)
from app.offboarding.service import (
    OffboardingPlanningError,
    OffboardingValidationError,
    create_offboarding_plan,
    get_offboarding_inventory,
)


router = APIRouter(prefix="/cases", tags=["offboarding"])


@router.get(
    "/{case_id}/offboarding/inventory",
    response_model=list[OffboardingResourceInventoryItem],
)
def read_offboarding_inventory(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> list[OffboardingResourceInventoryItem]:
    try:
        _, resources = get_offboarding_inventory(db, case_id)
        return [
            OffboardingResourceInventoryItem(
                resource_type=resource.resource_type,
                resource_key=resource.resource_key,
                status=resource.status,
                owner_id=resource.person_id,
                title=(resource.details_data or {}).get("title"),
                due_date=(resource.details_data or {}).get("due_date"),
            )
            for resource in resources
        ]
    except CaseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OffboardingPlanningError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/{case_id}/offboarding/plan",
    response_model=OffboardingPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_offboarding_plan(
    case_id: UUID,
    db: Session = Depends(get_db),
) -> OffboardingPlanResponse:
    try:
        return create_offboarding_plan(db, case_id)
    except CaseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (
        OffboardingPlanningError,
        PolicyContextStateError,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except OffboardingValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PolicyEvidenceNotFoundError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
