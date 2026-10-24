"""Agent access requests: the backend half of the MCP Access Gateway.

An agent asks (through the MCP adapter) for time-limited access. The request
becomes an ordinary ACCESS_REQUEST case with a one-step GRANT_TEMPORARY plan,
so it shares approval, execution, verification and audit with every other
case. Rules choose the tier (tiers.py); the LLM only writes a short note for
the approver, and a deterministic note is used if it is unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_requests.tiers import RiskTier, TierDecision, decide_tier
from app.audit.service import record_audit_event
from app.cases.policy_context import retrieve_case_policy_context
from app.config import get_settings
from app.enums import (
    ActionType,
    AppRole,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CasePriority,
    CaseState,
    CaseType,
    PlanState,
    ResourceState,
    ResourceType,
)
from app.execution.service import execute_approved_plan
from app.models import Approval, Case, CasePlan, CompanyResource, Person
from app.notifications.service import notify
from app.planning.schemas import GeneratedCasePlan, PlannedAction
from app.planning.service import build_case_action, build_policy_links
from app.planning.validation import validate_generated_plan


logger = logging.getLogger(__name__)

ORIGIN_MCP = "MCP_ACCESS_REQUEST"
ORIGIN_RELEASE = "MCP_RELEASE"
ORIGIN_EXPIRY = "GRANT_EXPIRY"


class AccessRequestError(ValueError):
    pass


class AccessRequestNotFoundError(AccessRequestError):
    pass


@dataclass(frozen=True)
class AccessRequestInput:
    system: str
    resource: str
    permission: str
    duration_minutes: int
    reason: str


EXPLANATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You brief an IT Owner on an AI agent's access request in at most two "
            "short sentences: who asks, for what and why, and which supplied policy "
            "clause applies. The risk tier is already decided by rules; do not "
            "change it or recommend a decision. Use only the facts given.",
        ),
        (
            "human",
            "Request:\n{request}\n\nRisk tier (decided by rules): {tier} because "
            "{tier_reasons}\n\nPolicy evidence:\n{evidence}",
        ),
    ]
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _it_owner(db: Session) -> Person:
    owner = db.scalar(
        select(Person).where(Person.app_role == AppRole.IT_OWNER).order_by(Person.name)
    )
    if owner is None:
        raise AccessRequestError("No IT Owner exists to approve agent access.")
    return owner


def _explain(
    agent: CompanyResource,
    request: AccessRequestInput,
    decision: TierDecision,
    evidence_text: str,
) -> str:
    fallback = (
        f"{(agent.details_data or {}).get('agent_name', agent.resource_key)} asks for "
        f"{request.permission} on {request.resource} for {request.duration_minutes} min: "
        f"{request.reason[:200]}. Tier {decision.tier.value} ({'; '.join(decision.reasons)}), "
        f"{decision.policy_rule}."
    )
    try:
        settings = get_settings()
        model = ChatOpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        message = (EXPLANATION_PROMPT | model).invoke(
            {
                "request": (
                    f"agent={(agent.details_data or {}).get('agent_name')}; "
                    f"permission={request.permission}; resource={request.resource}; "
                    f"duration_minutes={request.duration_minutes}; reason={request.reason}"
                ),
                "tier": decision.tier.value,
                "tier_reasons": "; ".join(decision.reasons),
                "evidence": evidence_text,
            }
        )
        text = str(message.content).strip()
        return text[:600] or fallback
    except Exception as error:  # noqa: BLE001 - the note is optional
        logger.warning("Approver explanation unavailable: %s", error)
        return fallback


def _agent_slug(agent: CompanyResource) -> str:
    return agent.resource_key.split(":", 1)[-1]


def _new_case(
    db: Session,
    agent: CompanyResource,
    facts: dict,
    priority: CasePriority,
) -> Case:
    case = Case(
        case_type=CaseType.ACCESS_REQUEST,
        subject_person_id=agent.person_id,
        created_by_id=agent.person_id,
        status=CaseState.PLANNING,
        priority=priority,
        case_facts={"agent_key": agent.resource_key, **facts},
    )
    db.add(case)
    db.flush()
    return case


def _plan_for(
    db: Session,
    case: Case,
    action: PlannedAction,
    summary: str,
    policy_context,
) -> CasePlan:
    generated = GeneratedCasePlan(summary=summary, actions=[action], warnings=[])
    validate_generated_plan(
        generated,
        case=case,
        policy_context=policy_context,
        resources=list(
            db.scalars(
                select(CompanyResource).where(
                    CompanyResource.person_id == case.subject_person_id
                )
            )
        ),
    )
    plan = CasePlan(
        case_id=case.id,
        revision=1,
        status=PlanState.PENDING_APPROVAL,
        summary=summary,
        plan_data=jsonable_encoder(generated.model_dump()),
    )
    db.add(plan)
    db.flush()
    db.add(build_case_action(case=case, plan=plan, action=action))
    db.add_all(build_policy_links(db, plan, generated, policy_context))
    return plan


def _agent_evidence_ids(policy_context) -> list[str]:
    ids = [
        item.evidence_id
        for item in policy_context.evidence
        if item.policy_code in {"ACCESS", "AGENT"}
    ]
    if not ids:
        raise AccessRequestError("No ACCESS or AGENT policy evidence was retrieved.")
    return ids


def _approve(
    db: Session,
    case: Case,
    plan: CasePlan,
    approver: Person,
    comment: str,
) -> Approval:
    approval = Approval(
        target_type=ApprovalTargetType.PLAN,
        target_id=plan.id,
        requested_by=case.created_by_id,
        assigned_to=approver.id,
        status=ApprovalState.APPROVED,
        comment=comment,
        decided_at=_now(),
    )
    db.add(approval)
    plan.status = PlanState.APPROVED
    case.status = CaseState.APPROVED
    db.flush()
    return approval


def create_access_request(
    db: Session,
    agent: CompanyResource,
    request: AccessRequestInput,
) -> Case:
    sponsor = db.get(Person, agent.person_id)
    decision = decide_tier(
        permission=request.permission,
        resource=request.resource,
        duration_minutes=request.duration_minutes,
        sponsor=sponsor,
    )
    case = _new_case(
        db,
        agent,
        {
            "origin": ORIGIN_MCP,
            "system": request.system,
            "resource": request.resource,
            "permission": request.permission,
            "duration_minutes": request.duration_minutes,
            "reason": request.reason,
            "tier": decision.tier.value,
            "tier_reasons": list(decision.reasons),
            "policy_rule": decision.policy_rule,
        },
        CasePriority.HIGH if decision.tier == RiskTier.HIGH else CasePriority.NORMAL,
    )
    record_audit_event(
        db,
        actor_type=AuditActorType.AGENT,
        event_type="AGENT_ACCESS_REQUESTED",
        entity_type="case",
        entity_id=case.id,
        after_data=dict(case.case_facts),
        correlation_id=case.id,
    )

    if decision.tier == RiskTier.DENY:
        case.status = CaseState.CANCELLED
        case.failure_reason = "Denied: " + "; ".join(decision.reasons)
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="AGENT_ACCESS_DENIED",
            entity_type="case",
            entity_id=case.id,
            after_data={"reasons": list(decision.reasons)},
            correlation_id=case.id,
        )
        db.commit()
        db.refresh(case)
        return case

    policy_context = retrieve_case_policy_context(db, case)
    evidence_ids = _agent_evidence_ids(policy_context)
    evidence_text = "\n".join(
        f"[{item.evidence_id}] {item.text[:600]}"
        for item in policy_context.evidence
        if item.evidence_id in evidence_ids
    )
    expires_at = _now() + timedelta(minutes=request.duration_minutes)
    grant_key = f"credential:{_agent_slug(agent)}:grant:{case.id.hex[:8]}"
    action = PlannedAction(
        sequence=1,
        action_type=ActionType.GRANT_TEMPORARY,
        resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key=grant_key,
        requested_data={
            "agent_key": agent.resource_key,
            "kind": "temporary_grant",
            "system": request.system,
            "repository": request.resource,
            "permission": request.permission.lower(),
            "duration_minutes": request.duration_minutes,
            "expires_at": expires_at.isoformat(),
        },
        reason=request.reason[:500] or "Agent access request.",
        evidence_ids=evidence_ids,
    )
    explanation = _explain(agent, request, decision, evidence_text)
    case.case_facts = {**case.case_facts, "approver_note": explanation}
    plan = _plan_for(
        db,
        case,
        action,
        f"Grant {request.permission} on {request.resource} to "
        f"{(agent.details_data or {}).get('agent_name', agent.resource_key)} "
        f"until {expires_at.isoformat(timespec='minutes')}.",
        policy_context,
    )
    approver = _it_owner(db)

    if decision.tier == RiskTier.LOW:
        _approve(db, case, plan, approver, f"Auto-approved: LOW tier ({decision.policy_rule}).")
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="AGENT_ACCESS_AUTO_APPROVED",
            entity_type="case_plan",
            entity_id=plan.id,
            after_data={"tier": decision.tier.value, "reasons": list(decision.reasons)},
            correlation_id=case.id,
        )
        db.commit()
        execute_approved_plan(db, plan.id)
        db.refresh(case)
        return case

    approval = Approval(
        target_type=ApprovalTargetType.PLAN,
        target_id=plan.id,
        requested_by=case.created_by_id,
        assigned_to=approver.id,
        status=ApprovalState.PENDING,
    )
    db.add(approval)
    case.status = CaseState.PENDING_APPROVAL
    db.commit()
    db.refresh(case)
    notify(
        event_type="APPROVAL_REQUESTED",
        title=f"Agent access: {request.permission} on {request.resource}",
        summary=explanation,
        link_path="approvals.html",
        audience=approver.name,
    )
    return case


def auto_execute_access_case(db: Session, approval: Approval) -> None:
    """After a human approves an ACCESS_REQUEST plan, run it right away:
    the agent is waiting, and the IT Owner's click is the go-ahead."""
    if approval.status != ApprovalState.APPROVED:
        return
    plan = db.get(CasePlan, approval.target_id)
    case = db.get(Case, plan.case_id) if plan else None
    if case is None or case.case_type != CaseType.ACCESS_REQUEST:
        return
    execute_approved_plan(db, plan.id)


def _grant_resource(db: Session, case: Case) -> CompanyResource | None:
    plan = db.scalar(select(CasePlan).where(CasePlan.case_id == case.id))
    if plan is None or not plan.actions:
        return None
    key = (plan.actions[0].requested_data or {}).get("resource_key")
    return db.scalar(select(CompanyResource).where(CompanyResource.resource_key == key))


def request_status(db: Session, agent: CompanyResource, case_id: UUID) -> dict:
    case = db.get(Case, case_id)
    if case is None or (case.case_facts or {}).get("agent_key") != agent.resource_key:
        raise AccessRequestNotFoundError(f"No access request {case_id} for this agent.")
    facts = case.case_facts or {}
    grant = _grant_resource(db, case)

    if case.status == CaseState.CANCELLED:
        state = "DENIED"
    elif case.status == CaseState.PENDING_APPROVAL:
        state = "PENDING_APPROVAL"
    elif case.status in {CaseState.FAILED, CaseState.HUMAN_REVIEW}:
        state = "FAILED"
    elif case.status == CaseState.COMPLETED and grant is not None:
        state = {
            ResourceState.ACTIVE: "ACTIVE",
            ResourceState.EXPIRED: "EXPIRED",
            ResourceState.REVOKED: "RELEASED",
        }.get(grant.status, grant.status.value)
    else:
        approval_rejected = db.scalar(
            select(Approval).where(Approval.status == ApprovalState.REJECTED)
            .join(CasePlan, CasePlan.id == Approval.target_id)
            .where(CasePlan.case_id == case.id)
        )
        state = "REJECTED" if approval_rejected else "APPROVED"

    return {
        "request_id": case.id,
        "state": state,
        "tier": facts.get("tier"),
        "tier_reasons": facts.get("tier_reasons", []),
        "approver_note": facts.get("approver_note"),
        "grant_key": grant.resource_key if grant else None,
        "expires_at": (grant.details_data or {}).get("expires_at") if grant else None,
        "detail": case.failure_reason,
    }


def _revoke_grant(db: Session, grant: CompanyResource, origin: str) -> Case:
    agent = db.scalar(
        select(CompanyResource).where(
            CompanyResource.resource_key == (grant.details_data or {}).get("agent_key")
        )
    )
    if agent is None:
        raise AccessRequestError(f"Grant {grant.resource_key} has no agent.")
    case = _new_case(
        db,
        agent,
        {"origin": origin, "grant_key": grant.resource_key},
        CasePriority.NORMAL,
    )
    policy_context = retrieve_case_policy_context(db, case)
    plan = _plan_for(
        db,
        case,
        PlannedAction(
            sequence=1,
            action_type=ActionType.REVOKE,
            resource_type=ResourceType.AGENT_CREDENTIAL,
            resource_key=grant.resource_key,
            requested_data={},
            reason=(
                "Temporary grant expired." if origin == ORIGIN_EXPIRY
                else "Agent released its temporary access."
            ),
            evidence_ids=_agent_evidence_ids(policy_context),
        ),
        f"Revoke {grant.resource_key} ({origin}).",
        policy_context,
    )
    _approve(db, case, plan, _it_owner(db), f"Automatic: {origin}.")
    db.commit()
    execute_approved_plan(db, plan.id)
    db.refresh(case)
    return case


def release_grant(db: Session, agent: CompanyResource, grant_key: str) -> Case:
    grant = db.scalar(select(CompanyResource).where(CompanyResource.resource_key == grant_key))
    if grant is None or (grant.details_data or {}).get("agent_key") != agent.resource_key:
        raise AccessRequestNotFoundError(f"No grant {grant_key} for this agent.")
    if grant.status != ResourceState.ACTIVE:
        raise AccessRequestError(f"Grant is already {grant.status.value}.")
    return _revoke_grant(db, grant, ORIGIN_RELEASE)


def due_grants(grants: list[CompanyResource], now: datetime) -> list[CompanyResource]:
    due = []
    for grant in grants:
        details = grant.details_data or {}
        if details.get("kind") != "temporary_grant" or grant.status != ResourceState.ACTIVE:
            continue
        expires_at = details.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) <= now:
            due.append(grant)
    return due


def expire_due_grants(db: Session, now: datetime | None = None) -> list[str]:
    """Revoke every temporary grant past its expiry, then mark it EXPIRED.
    Called by the n8n sweeper every 5 minutes; state stays in the backend."""
    now = now or _now()
    grants = list(
        db.scalars(
            select(CompanyResource).where(
                CompanyResource.resource_type == ResourceType.AGENT_CREDENTIAL,
                CompanyResource.status == ResourceState.ACTIVE,
            )
        )
    )
    expired = []
    for grant in due_grants(grants, now):
        _revoke_grant(db, grant, ORIGIN_EXPIRY)
        db.refresh(grant)
        if grant.status == ResourceState.REVOKED:
            grant.status = ResourceState.EXPIRED
            record_audit_event(
                db,
                actor_type=AuditActorType.SYSTEM,
                event_type="AGENT_GRANT_EXPIRED",
                entity_type="company_resource",
                entity_id=grant.id,
                after_data={"status": ResourceState.EXPIRED.value},
                correlation_id=grant.id,
            )
            db.commit()
            expired.append(grant.resource_key)
    return expired


def agent_grants(db: Session, agent: CompanyResource) -> list[CompanyResource]:
    return [
        grant
        for grant in db.scalars(
            select(CompanyResource).where(
                CompanyResource.resource_type == ResourceType.AGENT_CREDENTIAL
            )
        )
        if (grant.details_data or {}).get("agent_key") == agent.resource_key
    ]
