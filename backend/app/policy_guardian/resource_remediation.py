"""Remediation for RESOURCE impacts found by the live-resource re-check.

- A credential that may no longer write (REGENERATE) gets a one-step
  ACCESS_REQUEST case with a DOWNSCOPE action. It follows the normal path:
  IT Owner approval, executor (GitHub or mock), independent verification,
  audit. The impact is RESOLVED when that case completes.
- An agent whose sponsor changed (REVIEW) is re-certified by the IT Owner;
  the decision is recorded on the agent and audited.

Nothing here asks an LLM: the action follows from the rule that was broken.
"""
from __future__ import annotations

from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.cases.schemas import CasePolicyContextResponse, PolicyEvidenceResponse
from app.enums import (
    ActionType,
    AppRole,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CasePriority,
    CaseState,
    CaseType,
    ImpactRecommendedAction,
    ImpactState,
    PlanState,
    PolicyImpactTargetType,
    PolicyState,
    ResourceType,
)
from app.models import (
    Approval,
    Case,
    CasePlan,
    CompanyResource,
    Person,
    PolicyChange,
    PolicyImpact,
    PolicyVersion,
)
from app.notifications.service import notify
from app.planning.schemas import GeneratedCasePlan, PlannedAction
from app.planning.service import build_case_action, build_policy_links
from app.planning.validation import validate_generated_plan
from app.rag.policy_chunks import build_policy_chunks
from app.rag.policy_loader import split_policy_text


class ResourceRemediationError(ValueError):
    pass


class ResourceRemediationNotFoundError(ResourceRemediationError):
    pass


def _open_resource_impact(
    db: Session,
    impact_id: UUID,
    expected: ImpactRecommendedAction,
) -> tuple[PolicyImpact, CompanyResource]:
    impact = db.get(PolicyImpact, impact_id)
    if impact is None:
        raise ResourceRemediationNotFoundError(f"Impact does not exist: {impact_id}")
    if impact.target_type != PolicyImpactTargetType.RESOURCE:
        raise ResourceRemediationError("This impact does not target a live resource.")
    if impact.recommended_action != expected:
        raise ResourceRemediationError(
            f"This impact recommends {impact.recommended_action.value}, "
            f"not {expected.value}."
        )
    if impact.status != ImpactState.OPEN:
        raise ResourceRemediationError(
            f"Impact is already {impact.status.value}."
        )
    resource = db.get(CompanyResource, impact.target_id)
    if resource is None:
        raise ResourceRemediationNotFoundError("The impacted resource no longer exists.")
    return impact, resource


def _require_it_owner(db: Session, person_id: UUID) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise ResourceRemediationNotFoundError(f"Person does not exist: {person_id}")
    if person.app_role not in {AppRole.IT_OWNER, AppRole.ADMIN}:
        raise ResourceRemediationError(
            "Only an IT Owner or admin may remediate agent access."
        )
    return person


def _current_policy_evidence(db: Session, change: PolicyChange) -> CasePolicyContextResponse:
    """Evidence from the policy version that is CURRENT now (the new one)."""
    version = db.get(PolicyVersion, change.new_version_id)
    if version is None or version.status != PolicyState.CURRENT:
        raise ResourceRemediationError("The changed policy is no longer CURRENT.")
    chunks = build_policy_chunks(
        split_policy_text(version.content_text),
        policy_version_id=version.id,
        policy_code=version.policy_code,
        version_number=version.version_number,
        title=version.title,
        department=version.department,
        document_text=version.content_text,
    )
    return CasePolicyContextResponse(
        case_id=change.id,
        search_query=f"{version.policy_code} V{version.version_number} remediation",
        evidence=[
            PolicyEvidenceResponse(
                evidence_id=chunk.evidence_id,
                policy_code=version.policy_code,
                version_number=version.version_number,
                text=chunk.text,
                score=1.0,
            )
            for chunk in chunks
        ],
    )


def remediate_resource_impact(
    db: Session,
    impact_id: UUID,
    requested_by: UUID,
) -> tuple[PolicyImpact, Case, CasePlan, Approval]:
    impact, resource = _open_resource_impact(
        db, impact_id, ImpactRecommendedAction.REGENERATE
    )
    owner = _require_it_owner(db, requested_by)
    if resource.resource_type not in {ResourceType.AGENT_CREDENTIAL, ResourceType.GITHUB_ACCESS}:
        raise ResourceRemediationError("Only credentials and GitHub access can be downscoped.")

    change = db.get(PolicyChange, impact.policy_change_id)
    policy_context = _current_policy_evidence(db, change)
    generated = GeneratedCasePlan(
        summary=f"Downscope {resource.resource_key} to read-only after "
        f"{change.policy_code} V{change.new_version.version_number}.",
        actions=[
            PlannedAction(
                sequence=1,
                action_type=ActionType.DOWNSCOPE,
                resource_type=resource.resource_type,
                resource_key=resource.resource_key,
                requested_data={"permission": "read"},
                reason=impact.explanation[:500],
                evidence_ids=[item.evidence_id for item in policy_context.evidence],
            )
        ],
        warnings=[],
    )

    case = Case(
        case_type=CaseType.ACCESS_REQUEST,
        subject_person_id=resource.person_id,
        created_by_id=owner.id,
        status=CaseState.PENDING_APPROVAL,
        priority=CasePriority.HIGH,
        case_facts={
            "origin": "POLICY_GUARDIAN_REMEDIATION",
            "policy_impact_id": str(impact.id),
            "policy_change_id": str(change.id),
            "resource_key": resource.resource_key,
        },
    )
    db.add(case)
    db.flush()

    sponsor_resources = list(
        db.scalars(
            select(CompanyResource).where(CompanyResource.person_id == resource.person_id)
        )
    )
    validate_generated_plan(
        generated,
        case=case,
        policy_context=policy_context,
        resources=sponsor_resources,
    )

    plan = CasePlan(
        case_id=case.id,
        revision=1,
        status=PlanState.PENDING_APPROVAL,
        summary=generated.summary,
        plan_data=jsonable_encoder(generated.model_dump()),
    )
    db.add(plan)
    db.flush()
    db.add(build_case_action(case=case, plan=plan, action=generated.actions[0]))
    db.add_all(build_policy_links(db, plan, generated, policy_context))

    approval = Approval(
        target_type=ApprovalTargetType.PLAN,
        target_id=plan.id,
        requested_by=owner.id,
        assigned_to=owner.id,
        status=ApprovalState.PENDING,
    )
    db.add(approval)
    impact.status = ImpactState.REMEDIATING
    db.flush()

    record_audit_event(
        db,
        actor_type=AuditActorType.USER,
        actor_id=owner.id,
        event_type="POLICY_IMPACT_REMEDIATION_STARTED",
        entity_type="policy_impact",
        entity_id=impact.id,
        before_data={"status": ImpactState.OPEN.value},
        after_data={
            "status": impact.status.value,
            "case_id": str(case.id),
            "plan_id": str(plan.id),
            "approval_id": str(approval.id),
        },
        evidence_data={"resource_key": resource.resource_key},
        correlation_id=case.id,
    )
    db.commit()
    for item in (impact, case, plan, approval):
        db.refresh(item)

    notify(
        event_type="APPROVAL_REQUESTED",
        title=f"Remediation: downscope {resource.resource_key}",
        summary=impact.explanation,
        link_path=f"workspace.html?case={case.id}",
        audience=owner.name,
    )
    return impact, case, plan, approval


def recertify_resource_impact(
    db: Session,
    impact_id: UUID,
    decided_by: UUID,
) -> tuple[PolicyImpact, CompanyResource]:
    impact, resource = _open_resource_impact(
        db, impact_id, ImpactRecommendedAction.REVIEW
    )
    owner = _require_it_owner(db, decided_by)

    details = dict(resource.details_data or {})
    details["recertified_for_sponsor"] = str(resource.person_id)
    details["recertified_by"] = str(owner.id)
    resource.details_data = details
    impact.status = ImpactState.RESOLVED
    impact.resolved_by = owner.id

    record_audit_event(
        db,
        actor_type=AuditActorType.USER,
        actor_id=owner.id,
        event_type="AGENT_ACCESS_RECERTIFIED",
        entity_type="policy_impact",
        entity_id=impact.id,
        before_data={"status": ImpactState.OPEN.value},
        after_data={
            "status": impact.status.value,
            "sponsor_id": str(resource.person_id),
        },
        evidence_data={"resource_key": resource.resource_key},
        correlation_id=impact.policy_change_id,
    )
    db.commit()
    db.refresh(impact)
    db.refresh(resource)
    return impact, resource


def resolve_remediated_impact(db: Session, case: Case) -> None:
    """Called when a case completes: close the impact it was opened for."""
    impact_id = (case.case_facts or {}).get("policy_impact_id")
    if not impact_id:
        return
    impact = db.get(PolicyImpact, UUID(str(impact_id)))
    if impact is None or impact.status != ImpactState.REMEDIATING:
        return
    impact.status = ImpactState.RESOLVED
    impact.resolved_by = case.created_by_id
