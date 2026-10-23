from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.security.schemas import (
    AccessEventCreate,
    AccessEventRead,
    AlertReview,
)
from app.security.service import (
    create_and_score_access_event,
    list_open_security_alerts,
    review_access_event,
)


router = APIRouter(tags=["Security"])


@router.post(
    "/access-events",
    response_model=AccessEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_access_event(
    payload: AccessEventCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_and_score_access_event(db, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/security/alerts",
    response_model=list[AccessEventRead],
)
def get_security_alerts(
    db: Session = Depends(get_db),
):
    return list_open_security_alerts(db)


@router.post(
    "/access-events/{event_id}/review",
    response_model=AccessEventRead,
)
def review_security_alert(
    event_id: UUID,
    payload: AlertReview,
    db: Session = Depends(get_db),
):
    try:
        return review_access_event(
            db,
            event_id=event_id,
            reviewed_by=payload.reviewed_by,
            decision=payload.decision,
            comment=payload.comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
