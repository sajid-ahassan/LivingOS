from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.evidence.explanation import ExplanationNotFoundError, PlanExplanation, explain_plan
from app.evidence.report import EvidenceNotFoundError, build_evidence, render_html


router = APIRouter(tags=["evidence"])


@router.get("/plans/{plan_id}/explanation", response_model=PlanExplanation)
def read_plan_explanation(plan_id: UUID, db: Session = Depends(get_db)) -> PlanExplanation:
    """Data for the "why" panel of every plan step."""
    try:
        return explain_plan(db, plan_id)
    except ExplanationNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/cases/{case_id}/evidence", response_model=None)
def read_case_evidence(
    case_id: UUID,
    format: Literal["html", "json"] = "html",
    db: Session = Depends(get_db),
) -> Any:
    """Printable ISO/IEC 27001:2022 supporting-evidence report (or its JSON)."""
    try:
        evidence = build_evidence(db, case_id)
    except EvidenceNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    if format == "json":
        return evidence
    return HTMLResponse(render_html(evidence))


@router.get("/evaluation/latest", response_model=None)
def read_latest_evaluation() -> Any:
    """Numbers saved by `python -m app.scripts.run_evaluation`."""
    import json

    from app.scripts.run_evaluation import EVAL_PATH

    if not EVAL_PATH.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No evaluation yet; run python -m app.scripts.run_evaluation.",
        )
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))
