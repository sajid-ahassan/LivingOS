"""Read-only views for the frontend: lists the pages poll every few seconds.

Business state stays in the existing services; these endpoints only join and
shape it for display, so the UI never keeps its own copy in localStorage.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.database import get_db
from app.enums import ApprovalState, ImpactState, PolicyImpactTargetType
from app.evidence.explanation import policy_clauses
from app.models import (
    Approval,
    AuditEvent,
    Case,
    CaseAction,
    CasePlan,
    CompanyResource,
    LearningRecord,
    Person,
    PolicyChange,
    PolicyImpact,
    PolicyVersion,
)
from app.views.kpis import KPI_LABEL, latest_offboarding, ownership, policy_reasons


router = APIRouter(tags=["views"])
SEED_DIR = PROJECT_ROOT / "data" / "seed"


def _names(db: Session, ids) -> dict[UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {p.id: p.name for p in db.scalars(select(Person).where(Person.id.in_(ids)))}


def _case_row(case: Case, names: dict) -> dict[str, Any]:
    facts = case.case_facts or {}
    return {
        "id": case.id,
        "case_type": case.case_type.value,
        "status": case.status.value,
        "priority": case.priority.value,
        "subject_person_id": case.subject_person_id,
        "subject_name": names.get(case.subject_person_id),
        "created_by_name": names.get(case.created_by_id),
        "origin": facts.get("origin"),
        "agent_key": facts.get("agent_key"),
        "tier": facts.get("tier"),
        "failure_reason": case.failure_reason,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


@router.get("/cases", response_model=None)
def list_cases(limit: int = Query(40, ge=1, le=200), db: Session = Depends(get_db)) -> list[dict]:
    cases = list(db.scalars(select(Case).order_by(Case.created_at.desc()).limit(limit)))
    names = _names(db, [c.subject_person_id for c in cases] + [c.created_by_id for c in cases])
    return [_case_row(case, names) for case in cases]


def _verified_times(db: Session, action_ids) -> dict[UUID, datetime]:
    if not action_ids:
        return {}
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id.in_(action_ids),
            AuditEvent.event_type == "ACTION_VERIFIED",
        )
    )
    return {event.entity_id: event.occurred_at for event in events}


@router.get("/cases/{case_id}/plans", response_model=None)
def list_case_plans(case_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Case does not exist: {case_id}")
    plans = list(db.scalars(select(CasePlan).where(CasePlan.case_id == case.id).order_by(CasePlan.revision)))
    actions = [a for plan in plans for a in plan.actions]
    verified = _verified_times(db, [a.id for a in actions])
    approvals = list(db.scalars(select(Approval).where(Approval.target_id.in_([p.id for p in plans])))) if plans else []
    names = _names(db, [case.subject_person_id, case.created_by_id] + [a.assigned_to for a in approvals])

    def action_row(action: CaseAction) -> dict[str, Any]:
        data = action.requested_data or {}
        verification = action.verification_data or {}
        return {
            "id": action.id,
            "sequence": data.get("sequence"),
            "action_type": action.action_type.value,
            "resource_type": action.resource_type.value,
            "resource_key": data.get("resource_key"),
            "parameters": data.get("parameters") or {},
            "reason": data.get("reason"),
            "evidence_ids": data.get("evidence_ids") or [],
            "status": action.status.value,
            "attempt_count": action.attempt_count,
            "n8n_execution_id": action.n8n_execution_id,
            "verified_by": verification.get("source"),
            "github_observed": verification.get("github_observed"),
            "verified_at": verified.get(action.id),
            "error": action.error_message,
        }

    return {
        "case": {**_case_row(case, names), "case_facts": case.case_facts or {}},
        "plans": [
            {
                "id": plan.id,
                "revision": plan.revision,
                "status": plan.status.value,
                "summary": plan.summary,
                "parent_plan_id": plan.parent_plan_id,
                "correction_summary": plan.correction_summary,
                "created_at": plan.created_at,
                "targeted_questions": (plan.plan_data or {}).get("targeted_questions") or [],
                "approvals": [
                    {
                        "id": a.id,
                        "status": a.status.value,
                        "assigned_to": a.assigned_to,
                        "assigned_to_name": names.get(a.assigned_to),
                        "comment": a.comment,
                        "decided_at": a.decided_at,
                    }
                    for a in approvals if a.target_id == plan.id
                ],
                "actions": sorted(
                    (action_row(a) for a in plan.actions),
                    key=lambda row: int(row["sequence"] or 0),
                ),
            }
            for plan in plans
        ],
    }


@router.get("/approvals", response_model=None)
def list_approvals(
    approval_status: str = Query("PENDING", alias="status"),
    assigned_to: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(Approval).order_by(Approval.requested_at.desc()).limit(100)
    if approval_status != "ALL":
        query = query.where(Approval.status == ApprovalState(approval_status))
    if assigned_to:
        query = query.where(Approval.assigned_to == assigned_to)
    approvals = list(db.scalars(query))
    plans = {p.id: p for p in db.scalars(select(CasePlan).where(CasePlan.id.in_([a.target_id for a in approvals])))} if approvals else {}
    cases = {c.id: c for c in db.scalars(select(Case).where(Case.id.in_([p.case_id for p in plans.values()])))} if plans else {}
    names = _names(db, [a.assigned_to for a in approvals] + [c.subject_person_id for c in cases.values()])

    rows = []
    for approval in approvals:
        plan = plans.get(approval.target_id)
        case = cases.get(plan.case_id) if plan else None
        facts = (case.case_facts or {}) if case else {}
        lesson = (
            db.get(LearningRecord, approval.target_id)
            if approval.target_type.value == "LEARNING" else None
        )
        rows.append({
            "id": approval.id,
            "status": approval.status.value,
            "target_type": approval.target_type.value,
            "target_id": approval.target_id,
            "lesson": _lesson_candidate(lesson) if lesson else None,
            "lesson_case_id": lesson.source_case_id if lesson else None,
            "assigned_to": approval.assigned_to,
            "assigned_to_name": names.get(approval.assigned_to),
            "requested_at": approval.requested_at,
            "plan_id": plan.id if plan else None,
            "plan_summary": plan.summary if plan else None,
            "plan_revision": plan.revision if plan else None,
            "correction_summary": plan.correction_summary if plan else None,
            "action_count": len(plan.actions) if plan else 0,
            "case_id": case.id if case else None,
            "case_type": case.case_type.value if case else None,
            "subject_name": names.get(case.subject_person_id) if case else None,
            "origin": facts.get("origin"),
            "tier": facts.get("tier"),
            "tier_reasons": facts.get("tier_reasons") or [],
            "approver_note": facts.get("approver_note"),
            "agent_key": facts.get("agent_key"),
            "request": {k: facts.get(k) for k in ("resource", "permission", "duration_minutes", "reason") if k in facts},
        })
    return rows


@router.get("/policy-guardian/changes", response_model=None)
def list_policy_changes(db: Session = Depends(get_db)) -> list[dict]:
    changes = list(db.scalars(select(PolicyChange).order_by(PolicyChange.created_at.desc()).limit(20)))
    counts = Counter(
        (impact.policy_change_id, impact.status.value)
        for impact in db.scalars(select(PolicyImpact).where(PolicyImpact.policy_change_id.in_([c.id for c in changes])))
    ) if changes else Counter()
    return [
        {
            "id": change.id,
            "policy_code": change.policy_code,
            "old_version": change.old_version.version_number,
            "new_version": change.new_version.version_number,
            "overall_risk": change.overall_risk.value,
            "status": change.status.value,
            "created_at": change.created_at,
            "open_impacts": counts[(change.id, ImpactState.OPEN.value)] + counts[(change.id, ImpactState.REMEDIATING.value)],
        }
        for change in changes
    ]


def _lesson_candidate(record: LearningRecord) -> dict[str, Any]:
    # The lesson itself sits under "candidate", next to the revision diff.
    data = record.candidate_data or {}
    return data.get("candidate") or data


def _impact_target(db: Session, impact: PolicyImpact) -> dict[str, Any]:
    if impact.target_type == PolicyImpactTargetType.RESOURCE:
        resource = db.get(CompanyResource, impact.target_id)
        if resource is None:
            return {"label": "removed resource"}
        details = resource.details_data or {}
        return {
            "label": details.get("agent_name") or resource.resource_key,
            "resource_key": resource.resource_key,
            "resource_type": resource.resource_type.value,
            "agent_key": resource.resource_key if resource.resource_type.value == "AI_AGENT" else details.get("agent_key"),
            "owner_name": _names(db, [resource.person_id]).get(resource.person_id),
            "permission": details.get("permission"),
        }
    if impact.target_type == PolicyImpactTargetType.LEARNING:
        record = db.get(LearningRecord, impact.target_id)
        candidate = _lesson_candidate(record) if record else {}
        return {
            "label": "Approved lesson",
            "lesson": candidate.get("recommended_action"),
            "lesson_status": record.status.value if record else None,
        }
    plan = db.get(CasePlan, impact.target_id)
    case = db.get(Case, plan.case_id) if plan else None
    return {
        "label": f"{case.case_type.value} plan r{plan.revision}" if plan and case else "plan",
        "case_id": case.id if case else None,
        "subject_name": _names(db, [case.subject_person_id]).get(case.subject_person_id) if case else None,
    }


@router.get("/policy-guardian/changes/{change_id}/view", response_model=None)
def view_policy_change(change_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    change = db.get(PolicyChange, change_id)
    if change is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Policy change does not exist: {change_id}")
    old_clauses = policy_clauses(change.old_version.content_text)
    new_clauses = policy_clauses(change.new_version.content_text)
    old_texts = {c.text for c in old_clauses}
    impacts = list(db.scalars(select(PolicyImpact).where(PolicyImpact.policy_change_id == change.id)))
    summary = (change.diff_data or {}).get("guardian_summary") or {}
    return {
        "id": change.id,
        "policy_code": change.policy_code,
        "old_version": change.old_version.version_number,
        "new_version": change.new_version.version_number,
        "overall_risk": change.overall_risk.value,
        "created_at": change.created_at,
        "summary": summary,
        "old_clauses": [c.model_dump() for c in old_clauses],
        "new_clauses": [{**c.model_dump(), "added": c.text not in old_texts} for c in new_clauses],
        "impacts": [
            {
                "id": impact.id,
                "target_type": impact.target_type.value,
                "risk_level": impact.risk_level.value,
                "recommended_action": impact.recommended_action.value,
                "status": impact.status.value,
                "explanation": impact.explanation,
                "target": _impact_target(db, impact),
            }
            for impact in sorted(impacts, key=lambda i: (i.risk_level.value != "HIGH", i.target_type.value))
        ],
    }


@router.get("/demo/policies/{policy_code}/v{version}", response_model=None)
def read_seed_policy(policy_code: str, version: int) -> dict[str, Any]:
    """Seed policy text for the Guardian page (e.g. Access Policy V2)."""
    path = SEED_DIR / f"{policy_code.lower()}_policy_v{version}.md"
    if not path.exists() or path.parent != SEED_DIR:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such seed policy.")
    return {"policy_code": policy_code.upper(), "version": version, "content_text": path.read_text(encoding="utf-8")}


@router.get("/dashboard/kpis", response_model=None)
def dashboard_kpis(db: Session = Depends(get_db)) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    people = list(db.scalars(select(Person)))
    resources = list(db.scalars(select(CompanyResource)))
    actions = list(db.scalars(select(CaseAction)))
    cases = list(db.scalars(select(Case)))
    actions_by_case: dict = {}
    for action in actions:
        actions_by_case.setdefault(action.case_id, []).append(action)
    plan_case = {p.id: p.case_id for p in db.scalars(select(CasePlan))}
    approvals_by_case = Counter(
        plan_case.get(a.target_id)
        for a in db.scalars(select(Approval).where(Approval.status == ApprovalState.APPROVED))
    )
    return {
        "label": KPI_LABEL,
        **ownership(people, resources, now),
        **policy_reasons(actions),
        "latest_offboarding": latest_offboarding(
            cases, actions_by_case, _verified_times(db, [a.id for a in actions]), approvals_by_case
        ),
    }
