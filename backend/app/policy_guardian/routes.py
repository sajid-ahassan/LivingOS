from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.notifications.service import notify
from app.policy_guardian.remediation import (
    RemediationConflictError,
    RemediationNotFoundError,
    regenerate_plan_for_impact,
)
from app.policy_guardian.schemas import (
    PolicyActivationResponse,
    PolicyActivateRequest,
    PolicyChangeDetailResponse,
    RegenerateImpactRequest,
    RegenerateImpactResponse,
)
from app.policy_guardian.service import (
    GuardianConflictError,
    GuardianNotFoundError,
    activate_policy_change,
    get_policy_change,
)


router = APIRouter(prefix="/policy-guardian", tags=["policy-guardian"])


@router.post(
    "/activate",
    response_model=PolicyActivationResponse,
    status_code=status.HTTP_201_CREATED,
)
def activate_new_policy_version(
    request: PolicyActivateRequest,
    db: Session = Depends(get_db),
) -> PolicyActivationResponse:
    try:
        (
            old_version,
            new_version,
            change,
            impacts,
            stale_learning_ids,
            paused_case_ids,
            human_review_case_ids,
            indexed_chunks,
        ) = activate_policy_change(db, request)

        # Best-effort heads-up for the IT owner; never affects the response.
        notify(
            event_type="POLICY_IMPACTS_FOUND",
            title=(
                f"{new_version.policy_code} V{new_version.version_number} "
                f"affects {len(impacts)} item(s)"
            ),
            summary=(
                f"Policy Guardian found {len(impacts)} impact(s) after "
                f"{new_version.policy_code} V{new_version.version_number} was activated."
            ),
            link_path=f"guardian.html?change={change.id}",
        )

        return PolicyActivationResponse(
            old_version=old_version,
            new_version=new_version,
            policy_change=change,
            impacts=impacts,
            stale_learning_ids=stale_learning_ids,
            paused_case_ids=paused_case_ids,
            human_review_case_ids=human_review_case_ids,
            indexed_chunks=indexed_chunks,
        )
    except GuardianNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GuardianConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/changes/{change_id}",
    response_model=PolicyChangeDetailResponse,
)
def read_policy_change(
    change_id: UUID,
    db: Session = Depends(get_db),
) -> PolicyChangeDetailResponse:
    try:
        change, impacts = get_policy_change(db, change_id)
        return PolicyChangeDetailResponse(
            change=change,
            impacts=impacts,
        )
    except GuardianNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/impacts/{impact_id}/regenerate",
    response_model=RegenerateImpactResponse,
)
def regenerate_impacted_plan(
    impact_id: UUID,
    request: RegenerateImpactRequest,
    db: Session = Depends(get_db),
) -> RegenerateImpactResponse:
    try:
        return regenerate_plan_for_impact(
            db,
            impact_id,
            request,
        )
    except RemediationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RemediationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
