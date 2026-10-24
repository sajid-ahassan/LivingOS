"""The "why" panel: why each plan step exists, from stored data only.

For every step: the policy evidence it cites (version, status and the
policy's numbered clauses), approved lessons kept separate from policy, the
step's one-line reason, the deterministic validation outcome and whether the
planner needed its one repair. No chain-of-thought is stored or shown.
"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evaluation.attempts import PLAN_GENERATION_ATTEMPT
from app.models import AuditEvent, Case, CaseAction, CasePlan, LearningRecord, PolicyVersion


POLICY_EVIDENCE = re.compile(r"^POL-(?P<code>[A-Z_]+)-V(?P<version>\d+)-C(?P<chunk>\d+)$")
LESSON_EVIDENCE = re.compile(r"^MEM-(?P<learning_id>[0-9a-fA-F-]{36})-C\d+$")
CLAUSE_LINE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")


class ExplanationNotFoundError(ValueError):
    pass


class PolicyClause(BaseModel):
    number: int
    text: str


class PolicyEvidence(BaseModel):
    evidence_id: str
    policy_code: str
    version_number: int
    title: str | None
    status: str | None
    clauses: list[PolicyClause]


class LessonEvidence(BaseModel):
    evidence_id: str
    learning_id: str
    status: str | None
    recommended_action: str | None


class StepExplanation(BaseModel):
    sequence: int
    action_type: str
    resource_type: str
    resource_key: str
    reason: str | None
    action_status: str
    verified_by: str | None
    policy_evidence: list[PolicyEvidence]
    lessons: list[LessonEvidence]
    unresolved_evidence: list[str]


class PlanExplanation(BaseModel):
    plan_id: UUID
    case_id: UUID
    revision: int
    status: str
    summary: str
    origin: str
    correction_summary: str | None
    validation: dict[str, Any]
    steps: list[StepExplanation]


def policy_clauses(content_text: str) -> list[PolicyClause]:
    """Numbered rules of a policy document, in order."""
    clauses = []
    for line in content_text.splitlines():
        match = CLAUSE_LINE.match(line)
        if match:
            clauses.append(PolicyClause(number=int(match.group(1)), text=match.group(2)))
    return clauses


def _policy_evidence(db: Session, evidence_id: str) -> PolicyEvidence | None:
    match = POLICY_EVIDENCE.match(evidence_id)
    if not match:
        return None
    version = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_code == match["code"],
            PolicyVersion.version_number == int(match["version"]),
        )
    )
    return PolicyEvidence(
        evidence_id=evidence_id,
        policy_code=match["code"],
        version_number=int(match["version"]),
        title=version.title if version else None,
        status=version.status.value if version else None,
        clauses=policy_clauses(version.content_text) if version else [],
    )


def _lesson_evidence(db: Session, evidence_id: str) -> LessonEvidence | None:
    match = LESSON_EVIDENCE.match(evidence_id)
    if not match:
        return None
    record = db.get(LearningRecord, UUID(match["learning_id"]))
    candidate = (record.candidate_data or {}) if record else {}
    return LessonEvidence(
        evidence_id=evidence_id,
        learning_id=match["learning_id"],
        status=record.status.value if record else None,
        recommended_action=candidate.get("recommended_action"),
    )


def _generation_validation(db: Session, case_id: UUID) -> dict[str, Any]:
    attempt = db.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.correlation_id == case_id,
            AuditEvent.event_type == PLAN_GENERATION_ATTEMPT,
        )
        .order_by(AuditEvent.occurred_at.desc())
        .limit(1)
    )
    data = (attempt.after_data or {}) if attempt else {}
    return {
        "deterministic_validation": "passed",
        "repair_used": (data.get("repair_count") or 0) > 0 if attempt else None,
        "first_pass_valid": data.get("first_pass_valid") if attempt else None,
    }


def explain_plan(db: Session, plan_id: UUID) -> PlanExplanation:
    plan = db.get(CasePlan, plan_id)
    if plan is None:
        raise ExplanationNotFoundError(f"Plan does not exist: {plan_id}")
    case = db.get(Case, plan.case_id)

    actions = sorted(
        db.scalars(select(CaseAction).where(CaseAction.plan_id == plan.id)),
        key=lambda action: int((action.requested_data or {}).get("sequence", 0)),
    )
    steps = []
    for action in actions:
        data = action.requested_data or {}
        policies, lessons, unresolved = [], [], []
        for evidence_id in data.get("evidence_ids") or []:
            policy = _policy_evidence(db, evidence_id)
            lesson = None if policy else _lesson_evidence(db, evidence_id)
            if policy:
                policies.append(policy)
            elif lesson:
                lessons.append(lesson)
            else:
                unresolved.append(evidence_id)
        steps.append(
            StepExplanation(
                sequence=int(data.get("sequence", 0)),
                action_type=action.action_type.value,
                resource_type=action.resource_type.value,
                resource_key=str(data.get("resource_key")),
                reason=data.get("reason"),
                action_status=action.status.value,
                verified_by=(action.verification_data or {}).get("source"),
                policy_evidence=policies,
                lessons=lessons,
                unresolved_evidence=unresolved,
            )
        )

    if plan.parent_plan_id:
        origin, validation = "MANAGER_REVISION", {"deterministic_validation": "passed"}
    elif (case.case_facts or {}).get("origin"):
        origin = str(case.case_facts["origin"])
        validation = {"deterministic_validation": "passed"}
    else:
        origin, validation = "AI_PLANNER", _generation_validation(db, case.id)

    return PlanExplanation(
        plan_id=plan.id,
        case_id=case.id,
        revision=plan.revision,
        status=plan.status.value,
        summary=plan.summary or "",
        origin=origin,
        correction_summary=plan.correction_summary,
        validation=validation,
        steps=steps,
    )
