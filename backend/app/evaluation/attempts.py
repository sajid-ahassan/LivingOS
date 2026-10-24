"""Record every AI plan generation attempt for the evaluation panel.

Written in its own session so a failed attempt is kept even when the
business transaction that called the planner rolls back.
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.audit.service import record_audit_event
from app.database import SessionLocal
from app.enums import AuditActorType


logger = logging.getLogger(__name__)

PLAN_GENERATION_ATTEMPT = "PLAN_GENERATION_ATTEMPT"


def record_plan_generation_attempt(
    *,
    case_id: UUID,
    case_type: str,
    repair_count: int,
    valid: bool,
    errors: list[str] | None = None,
) -> None:
    try:
        with SessionLocal() as db:
            record_audit_event(
                db,
                actor_type=AuditActorType.LLM,
                event_type=PLAN_GENERATION_ATTEMPT,
                entity_type="case",
                entity_id=case_id,
                after_data={
                    "case_type": case_type,
                    "repair_count": repair_count,
                    "valid": valid,
                    "first_pass_valid": valid and repair_count == 0,
                    "error_count": len(errors or []),
                },
                evidence_data={"errors": (errors or [])[:10]},
                correlation_id=case_id,
            )
            db.commit()
    except Exception as error:  # noqa: BLE001 - metrics must never break planning
        logger.warning("Could not record plan generation attempt: %s", error)
