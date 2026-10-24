from __future__ import annotations

import difflib
import hashlib
import re
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_openai import ChatOpenAI
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event
from app.config import get_settings
from app.enums import (
    ActionState,
    AuditActorType,
    CaseState,
    ImpactRecommendedAction,
    ImpactState,
    LearningState,
    PlanState,
    PolicyChangeState,
    PolicyImpactTargetType,
    PolicyLinkSubjectType,
    PolicyState,
    ResourceType,
    RiskLevel,
)
from app.models import (
    Case,
    CaseAction,
    CasePlan,
    CompanyResource,
    LearningRecord,
    Person,
    PolicyChange,
    PolicyImpact,
    PolicyLink,
    PolicyVersion,
)
from app.policy_guardian.prompt import GUARDIAN_CHANGE_PROMPT
from app.policy_guardian.schemas import GuardianChangeSummary, PolicyActivateRequest
from app.policy_guardian.graph_runner import analyze_policy_change_via_graph
from app.policy_guardian.resource_rules import (
    COMPLETED_TRAINING_STATES,
    LIVE_STATES,
    ResourceContext,
    evaluate_resources,
    newly_added_rules,
)
from app.rag.policy_chunks import build_policy_chunks
from app.rag.policy_loader import split_policy_text
from app.rag.policy_registry import register_policy_draft
from app.rag.policy_vector_store import count_policy_chunks, store_policy_chunks
from app.rag.qdrant_client import get_qdrant_client


class GuardianError(ValueError):
    pass


class GuardianNotFoundError(GuardianError):
    pass


class GuardianConflictError(GuardianError):
    pass


def _normalize_policy_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _deterministic_diff(old_text: str, new_text: str) -> dict:
    old_lines = [line for line in old_text.splitlines() if line.strip()]
    new_lines = [line for line in new_text.splitlines() if line.strip()]

    raw = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="old_policy",
            tofile="new_policy",
            lineterm="",
        )
    )

    added = [
        line[1:].strip()
        for line in raw
        if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:].strip()
        for line in raw
        if line.startswith("-") and not line.startswith("---")
    ]

    return {
        "added_lines": added[:100],
        "removed_lines": removed[:100],
        "unified_diff": "\n".join(raw)[:20000],
    }


def _guardian_summary(
    policy_code: str,
    old_text: str,
    new_text: str,
    deterministic_diff: dict,
) -> GuardianChangeSummary:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    chain = GUARDIAN_CHANGE_PROMPT | llm.with_structured_output(
        GuardianChangeSummary
    )
    return chain.invoke(
        {
            "policy_code": policy_code,
            "deterministic_diff": deterministic_diff["unified_diff"],
            "old_policy": old_text,
            "new_policy": new_text,
        }
    )


def _current_policy(db: Session, policy_code: str) -> PolicyVersion:
    policy = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_code == policy_code,
            PolicyVersion.status == PolicyState.CURRENT,
        )
    )
    if policy is None:
        raise GuardianNotFoundError(
            f"No CURRENT policy exists for code {policy_code}."
        )
    return policy


def _plan_contains_sensitive_access(plan: CasePlan) -> bool:
    data = dict(plan.plan_data or {})
    actions = list(data.get("actions") or []) or [
        *(data.get("revocations") or []),
        *(data.get("asset_returns") or []),
        *(data.get("reassignments") or []),
    ]
    sensitive = {
        ResourceType.GITHUB_ACCESS.value,
        ResourceType.EMAIL_ACCOUNT.value,
        ResourceType.AI_AGENT.value,
        ResourceType.AGENT_CREDENTIAL.value,
    }
    return any(
        str(item.get("resource_type") or "") in sensitive
        for item in actions
    )


def _has_dispatched_open_action(db: Session, plan_id: UUID) -> bool:
    return (
        db.scalar(
            select(CaseAction.id).where(
                CaseAction.plan_id == plan_id,
                CaseAction.status.in_(
                    [
                        ActionState.DISPATCHED,
                        ActionState.SUCCEEDED,
                        ActionState.RETRYING,
                    ]
                ),
            )
        )
        is not None
    )


def _remove_learning_point(record: LearningRecord) -> None:
    if record.qdrant_point_id is None:
        return

    settings = get_settings()
    collection = getattr(
        settings,
        "qdrant_memory_collection",
        "approved_operational_memory_v1",
    )
    client = get_qdrant_client()
    try:
        if client.collection_exists(collection):
            client.delete(
                collection_name=collection,
                points_selector=PointIdsList(
                    points=[str(record.qdrant_point_id)]
                ),
                wait=True,
            )
    finally:
        client.close()


def _set_policy_payload_status(
    policy_version_id: UUID,
    status: str,
) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    try:
        client.set_payload(
            collection_name=settings.qdrant_policy_collection,
            payload={"status": status},
            points=Filter(
                must=[
                    FieldCondition(
                        key="policy_version_id",
                        match=MatchValue(value=str(policy_version_id)),
                    )
                ]
            ),
            wait=True,
        )
    finally:
        client.close()


def _create_learning_impact(
    db: Session,
    change: PolicyChange,
    link: PolicyLink,
    record: LearningRecord,
) -> PolicyImpact:
    impact = PolicyImpact(
        policy_change_id=change.id,
        target_type=PolicyImpactTargetType.LEARNING,
        target_id=record.id,
        risk_level=RiskLevel.HIGH,
        explanation=(
            "Approved organizational memory depends on the archived policy "
            "version and cannot remain authoritative for retrieval."
        ),
        recommended_action=ImpactRecommendedAction.MARK_STALE,
        status=ImpactState.OPEN,
    )
    db.add(impact)

    if record.status == LearningState.APPROVED:
        record.status = LearningState.STALE
        record.stale_reason = (
            f"Policy {change.policy_code} changed from "
            f"{change.old_version.version_number} to "
            f"{change.new_version.version_number}."
        )

    return impact


def _create_plan_impact(
    db: Session,
    change: PolicyChange,
    link: PolicyLink,
    plan: CasePlan,
) -> tuple[PolicyImpact, UUID | None, UUID | None]:
    case = db.get(Case, plan.case_id)
    if case is None:
        raise GuardianConflictError(
            f"Linked plan {plan.id} has no case."
        )

    paused_case_id = None
    human_review_case_id = None

    if case.status == CaseState.COMPLETED:
        risk = RiskLevel.LOW
        action = ImpactRecommendedAction.NO_ACTION
        explanation = (
            "The policy-linked case is already completed. Keep the historical "
            "record; no automatic reversal is performed."
        )
    elif _has_dispatched_open_action(db, plan.id):
        risk = RiskLevel.HIGH
        action = ImpactRecommendedAction.REVIEW
        explanation = (
            "An action is already in flight under the archived policy. "
            "Automatic re-dispatch is unsafe; external state requires review."
        )
        case.status = CaseState.HUMAN_REVIEW
        human_review_case_id = case.id
    elif plan.status in (PlanState.PENDING_APPROVAL, PlanState.APPROVED):
        if _plan_contains_sensitive_access(plan):
            risk = RiskLevel.HIGH
            explanation = (
                "Pending or approved sensitive-access plan depends on the "
                "archived policy and must be regenerated under the new version."
            )
        else:
            risk = RiskLevel.MEDIUM
            explanation = (
                "Pending or approved plan depends on the archived policy and "
                "requires review under the new version."
            )

        action = ImpactRecommendedAction.REGENERATE
        plan.status = PlanState.STALE
        case.status = CaseState.PAUSED
        paused_case_id = case.id
    else:
        risk = RiskLevel.LOW
        action = ImpactRecommendedAction.REVIEW
        explanation = (
            "The linked plan is not active. Preserve it for history and review "
            "only if the case is reopened."
        )

    impact = PolicyImpact(
        policy_change_id=change.id,
        target_type=PolicyImpactTargetType.PLAN,
        target_id=plan.id,
        risk_level=risk,
        explanation=explanation,
        recommended_action=action,
        status=ImpactState.OPEN,
    )
    db.add(impact)
    return impact, paused_case_id, human_review_case_id


def _recheck_live_resources(
    db: Session,
    change: PolicyChange,
    old_version: PolicyVersion,
    old_text: str,
    new_text: str,
) -> list[PolicyImpact]:
    """Flag live agent access granted under the old version that breaks a
    newly added rule. Deterministic: links and rules decide, never the LLM."""
    rules = newly_added_rules(old_text, new_text)
    if not rules:
        return []

    linked_plan_ids = set(
        db.scalars(
            select(PolicyLink.subject_id).where(
                PolicyLink.subject_type == PolicyLinkSubjectType.PLAN,
                PolicyLink.policy_version_id == old_version.id,
            )
        )
    )
    if not linked_plan_ids:
        return []

    resources = list(
        db.scalars(
            select(CompanyResource)
            .join(CaseAction, CaseAction.id == CompanyResource.source_action_id)
            .where(
                CaseAction.plan_id.in_(linked_plan_ids),
                CompanyResource.resource_type.in_(
                    [
                        ResourceType.AI_AGENT,
                        ResourceType.AGENT_CREDENTIAL,
                        ResourceType.GITHUB_ACCESS,
                    ]
                ),
                CompanyResource.status.in_(list(LIVE_STATES)),
            )
        )
    )

    contexts = []
    for resource in resources:
        trainings = db.scalars(
            select(CompanyResource).where(
                CompanyResource.person_id == resource.person_id,
                CompanyResource.resource_type == ResourceType.TRAINING,
                CompanyResource.status.in_(list(COMPLETED_TRAINING_STATES)),
            )
        )
        contexts.append(
            ResourceContext(
                resource=resource,
                sponsor=db.get(Person, resource.person_id),
                sponsor_training=frozenset(
                    str((training.details_data or {}).get("catalog_key"))
                    for training in trainings
                ),
            )
        )

    impacts = []
    for finding in evaluate_resources(rules, contexts):
        impact = PolicyImpact(
            policy_change_id=change.id,
            target_type=PolicyImpactTargetType.RESOURCE,
            target_id=finding.resource.id,
            risk_level=finding.risk_level,
            explanation=f"[{finding.rule_id}] {finding.explanation}",
            recommended_action=finding.recommended_action,
            status=ImpactState.OPEN,
        )
        db.add(impact)
        impacts.append(impact)
    db.flush()
    return impacts


def activate_policy_change(
    db: Session,
    request: PolicyActivateRequest,
) -> tuple[
    PolicyVersion,
    PolicyVersion,
    PolicyChange,
    list[PolicyImpact],
    list[UUID],
    list[UUID],
    list[UUID],
    int,
]:
    policy_code = request.policy_code.strip().upper()
    old_version = _current_policy(db, policy_code)

    if request.version_number != old_version.version_number + 1:
        raise GuardianConflictError(
            f"Version must be exactly V{old_version.version_number + 1}."
        )

    new_text = _normalize_policy_text(request.content_text)
    old_text = _normalize_policy_text(old_version.content_text)

    new_hash = hashlib.sha256(new_text.encode("utf-8")).hexdigest()
    if new_hash == old_version.content_hash:
        raise GuardianConflictError(
            "New policy content is identical to the current version."
        )

    new_version = register_policy_draft(
        db,
        policy_code=policy_code,
        title=request.title,
        version_number=request.version_number,
        department=request.department,
        effective_from=request.effective_from,
        content_text=new_text,
        uploaded_by=request.uploaded_by,
    )

    chunks = build_policy_chunks(
        split_policy_text(new_text),
        policy_version_id=new_version.id,
        policy_code=new_version.policy_code,
        version_number=new_version.version_number,
        title=new_version.title,
        department=new_version.department,
        document_text=new_text,
    )
    # Mark payload as DRAFT while indexed.
    for chunk in chunks:
        chunk.payload["status"] = PolicyState.DRAFT.value

    store_policy_chunks(chunks)
    indexed_chunks = count_policy_chunks(new_version.id)
    if indexed_chunks != len(chunks):
        raise GuardianConflictError(
            "New policy was not fully indexed in Qdrant."
        )

    graph_result = analyze_policy_change_via_graph(
        db=db,
        old_version=old_version,
        new_version=new_version,
        old_text=old_text,
        new_text=new_text,
        deterministic_diff_fn=_deterministic_diff,
        summarize_changes_fn=_guardian_summary,
    )

    deterministic = graph_result.deterministic
    summary = graph_result.summary
    links = graph_result.links

    change = PolicyChange(
        policy_code=policy_code,
        old_version_id=old_version.id,
        new_version_id=new_version.id,
        diff_data={
            "deterministic": deterministic,
            "guardian_summary": jsonable_encoder(summary),
        },
        overall_risk=summary.overall_risk,
        status=PolicyChangeState.ANALYZED,
    )
    db.add(change)
    db.flush()

    impacts: list[PolicyImpact] = []
    stale_records: list[LearningRecord] = []
    stale_learning_ids: list[UUID] = []
    paused_case_ids: list[UUID] = []
    human_review_case_ids: list[UUID] = []

    for link in links:
        if link.subject_type == PolicyLinkSubjectType.LEARNING:
            record = db.get(LearningRecord, link.subject_id)
            if record is None:
                continue
            impacts.append(
                _create_learning_impact(
                    db,
                    change,
                    link,
                    record,
                )
            )
            if record.status == LearningState.STALE:
                stale_records.append(record)
                stale_learning_ids.append(record.id)

        elif link.subject_type == PolicyLinkSubjectType.PLAN:
            plan = db.get(CasePlan, link.subject_id)
            if plan is None:
                continue
            impact, paused_id, review_id = _create_plan_impact(
                db,
                change,
                link,
                plan,
            )
            impacts.append(impact)
            if paused_id:
                paused_case_ids.append(paused_id)
            if review_id:
                human_review_case_ids.append(review_id)

    impacts.extend(
        _recheck_live_resources(db, change, old_version, old_text, new_text)
    )

    # Archive V1 first so the unique "one CURRENT per policy" index is safe.
    old_version.status = PolicyState.ARCHIVED
    db.flush()
    new_version.status = PolicyState.CURRENT

    record_audit_event(
        db,
        actor_type=AuditActorType.USER,
        actor_id=request.uploaded_by,
        event_type="POLICY_VERSION_ACTIVATED",
        entity_type="policy_change",
        entity_id=change.id,
        before_data={
            "policy_version_id": str(old_version.id),
            "version_number": old_version.version_number,
            "status": PolicyState.CURRENT.value,
        },
        after_data={
            "policy_version_id": str(new_version.id),
            "version_number": new_version.version_number,
            "status": PolicyState.CURRENT.value,
        },
        evidence_data={
            "impact_count": len(impacts),
            "stale_learning_ids": [str(i) for i in stale_learning_ids],
            "paused_case_ids": [str(i) for i in paused_case_ids],
        },
        correlation_id=change.id,
    )

    db.commit()
    db.refresh(old_version)
    db.refresh(new_version)
    db.refresh(change)

    # Vector maintenance happens only after PostgreSQL is authoritative.
    try:
        _set_policy_payload_status(
            old_version.id,
            PolicyState.ARCHIVED.value,
        )
        _set_policy_payload_status(
            new_version.id,
            PolicyState.CURRENT.value,
        )

        for record in stale_records:
            _remove_learning_point(record)
            record = db.get(LearningRecord, record.id)
            record.qdrant_point_id = None

        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="POLICY_VECTOR_STATE_UPDATED",
            entity_type="policy_change",
            entity_id=change.id,
            after_data={"vector_maintenance": "completed"},
            correlation_id=change.id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="POLICY_VECTOR_STATE_FAILED",
            entity_type="policy_change",
            entity_id=change.id,
            evidence_data={"error": str(exc)[:1000]},
            correlation_id=change.id,
        )
        db.commit()
        raise GuardianConflictError(
            "PostgreSQL policy activation succeeded, but Qdrant maintenance "
            "failed. Rebuild indexes before further planning."
        ) from exc

    impacts = list(
        db.scalars(
            select(PolicyImpact).where(
                PolicyImpact.policy_change_id == change.id
            )
        )
    )

    return (
        old_version,
        new_version,
        change,
        impacts,
        sorted(set(stale_learning_ids), key=str),
        sorted(set(paused_case_ids), key=str),
        sorted(set(human_review_case_ids), key=str),
        indexed_chunks,
    )


def get_policy_change(
    db: Session,
    change_id: UUID,
) -> tuple[PolicyChange, list[PolicyImpact]]:
    change = db.get(PolicyChange, change_id)
    if change is None:
        raise GuardianNotFoundError(
            f"Policy change does not exist: {change_id}"
        )

    impacts = list(
        db.scalars(
            select(PolicyImpact)
            .where(PolicyImpact.policy_change_id == change.id)
            .order_by(PolicyImpact.created_at.asc())
        )
    )
    return change, impacts
