from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.learning.graph_runner import generate_learning_candidate_via_graph

from app.audit.service import record_audit_event
from app.enums import (
    ActionState,
    AppRole,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CaseState,
    LearningState,
    LearningTriggerType,
    PolicyLinkSubjectType,
    PlanState,
    PolicyState,
)
from app.config import get_settings
from app.learning.prompt import LEARNING_CANDIDATE_PROMPT
from app.learning.schemas import LearningCandidate, LearningSearchRequest
from app.models import (
    Approval,
    Case,
    CaseAction,
    CasePlan,
    CompanyResource,
    LearningRecord,
    Person,
    PolicyLink,
    PolicyVersion,
)
from app.rag.learning_memory import (
    MemorySearchResult,
    build_learning_identity,
    search_learning_memory,
    upsert_learning_memory,
)


class LearningError(ValueError):
    pass


class LearningNotFoundError(LearningError):
    pass


class LearningConflictError(LearningError):
    pass


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.I,
)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|api[_ -]?key|secret|token|private[_ -]?key)\b\s*[:=]\s*\S+"
)


def _canonical_scope(scope: dict) -> str:
    normalized = {
        "case_types": sorted(str(item) for item in scope.get("case_types") or []),
        "departments": sorted(str(item) for item in scope.get("departments") or []),
        "roles": sorted(str(item) for item in scope.get("roles") or []),
        "sensitivity": str(scope.get("sensitivity") or "INTERNAL"),
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def _sanitize_for_memory(db: Session, record: LearningRecord) -> tuple[str, bool]:
    text = record.memory_text.strip()
    original = text

    source_case = record.source_case
    subject = db.get(Person, source_case.subject_person_id)
    if subject is not None and subject.name.strip():
        text = re.sub(
            re.escape(subject.name.strip()),
            "[EMPLOYEE]",
            text,
            flags=re.I,
        )

    resources = list(
        db.scalars(
            select(CompanyResource).where(
                CompanyResource.person_id == source_case.subject_person_id
            )
        )
    )
    for resource in resources:
        if resource.resource_key:
            text = text.replace(resource.resource_key, "[RESOURCE]")

    text = _SECRET_RE.sub("[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _UUID_RE.sub("[REDACTED_ID]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text, text != original


def _validate_source_ready(db: Session, record: LearningRecord) -> None:
    case = record.source_case
    if case.status != CaseState.COMPLETED:
        raise LearningConflictError(
            f"Source case must be COMPLETED. Current status: {case.status.value}"
        )

    unverified = list(
        db.scalars(
            select(CaseAction).where(
                CaseAction.case_id == case.id,
                CaseAction.plan_id == record.source_plan_id,
                CaseAction.status != ActionState.VERIFIED,
            )
        )
    )
    if unverified:
        raise LearningConflictError(
            "Every required source action must be VERIFIED before learning is indexed."
        )


def _copy_current_policy_links(db: Session, record: LearningRecord) -> list[UUID]:
    source_links = list(
        db.scalars(
            select(PolicyLink).where(
                PolicyLink.subject_type == PolicyLinkSubjectType.PLAN,
                PolicyLink.subject_id == record.source_plan_id,
            )
        )
    )
    if not source_links:
        raise LearningConflictError(
            "The source plan has no policy links, so the learning record cannot be governed."
        )

    policy_version_ids: list[UUID] = []
    for source_link in source_links:
        policy = db.get(PolicyVersion, source_link.policy_version_id)
        if policy is None or policy.status != PolicyState.CURRENT:
            raise LearningConflictError(
                "A policy used by the source plan is no longer CURRENT. Revalidate the learning candidate."
            )

        policy_version_ids.append(policy.id)
        existing = db.scalar(
            select(PolicyLink).where(
                PolicyLink.policy_version_id == policy.id,
                PolicyLink.subject_type == PolicyLinkSubjectType.LEARNING,
                PolicyLink.subject_id == record.id,
            )
        )
        if existing is None:
            db.add(
                PolicyLink(
                    policy_version_id=policy.id,
                    subject_type=PolicyLinkSubjectType.LEARNING,
                    subject_id=record.id,
                    use_reason="Approved organizational learning",
                    evidence_ids=list(source_link.evidence_ids or []),
                )
            )

    return sorted(set(policy_version_ids), key=str)


def index_approved_learning(
    db: Session,
    learning_record_id: UUID,
) -> tuple[LearningRecord, str, bool, list[UUID]]:
    record = db.get(LearningRecord, learning_record_id)
    if record is None:
        raise LearningNotFoundError(
            f"Learning record does not exist: {learning_record_id}"
        )
    if record.status != LearningState.APPROVED:
        raise LearningConflictError(
            f"Only APPROVED learning can be indexed. Current status: {record.status.value}"
        )
    if record.stale_reason:
        raise LearningConflictError("STALE learning cannot be indexed.")

    _validate_source_ready(db, record)

    sanitized_text, changed = _sanitize_for_memory(db, record)
    if not sanitized_text:
        raise LearningConflictError("Sanitized learning text is empty.")

    record.memory_text = sanitized_text
    record.content_hash = hashlib.sha256(
        (sanitized_text + "\n" + _canonical_scope(record.scope)).encode("utf-8")
    ).hexdigest()

    policy_version_ids = _copy_current_policy_links(db, record)

    # Commit PostgreSQL governance metadata before touching Qdrant.
    record_audit_event(
        db,
        actor_type=AuditActorType.SYSTEM,
        event_type="LEARNING_APPROVED",
        entity_type="learning_record",
        entity_id=record.id,
        after_data={
            "status": record.status.value,
            "sanitized_before_indexing": changed,
        },
        evidence_data={
            "policy_version_ids": [str(item) for item in policy_version_ids],
        },
        correlation_id=record.source_case_id,
    )
    db.commit()
    db.refresh(record)

    evidence_id, expected_point_id = build_learning_identity(
        record.id,
        record.content_hash,
    )

    try:
        _, point_id = upsert_learning_memory(
            learning_id=record.id,
            trigger_type=record.trigger_type.value,
            memory_text=record.memory_text,
            content_hash=record.content_hash,
            scope=record.scope,
            policy_version_ids=policy_version_ids,
        )
        if point_id != expected_point_id:
            raise RuntimeError("Unexpected learning point identifier.")

        record.qdrant_point_id = point_id
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="LEARNING_INDEXED",
            entity_type="learning_record",
            entity_id=record.id,
            after_data={
                "qdrant_point_id": str(point_id),
                "evidence_id": evidence_id,
            },
            evidence_data={
                "policy_version_ids": [str(item) for item in policy_version_ids],
            },
            correlation_id=record.source_case_id,
        )
        db.commit()
        db.refresh(record)
    except Exception as exc:
        db.rollback()
        record = db.get(LearningRecord, learning_record_id)
        record.qdrant_point_id = None
        record_audit_event(
            db,
            actor_type=AuditActorType.SYSTEM,
            event_type="LEARNING_INDEX_FAILED",
            entity_type="learning_record",
            entity_id=record.id,
            evidence_data={"error": str(exc)[:500]},
            correlation_id=record.source_case_id,
        )
        db.commit()
        raise

    return record, evidence_id, changed, policy_version_ids


def search_approved_learning(
    request: LearningSearchRequest,
) -> list[MemorySearchResult]:
    return search_learning_memory(
        query=request.query,
        case_type=request.case_type.value,
        department=request.department,
        role=request.role,
        sensitivity=request.sensitivity,
        top_k=request.top_k,
    )


def _normalized_action(action: dict) -> dict:
    return {
        "action_type": str(action.get("action_type") or ""),
        "resource_type": str(action.get("resource_type") or ""),
        "resource_key": str(action.get("resource_key") or ""),
        "requested_data": dict(action.get("requested_data") or {}),
    }


def _plan_actions(plan_data: dict | None) -> list[dict]:
    """Actions of either plan shape: GeneratedCasePlan ("actions") or the
    offboarding planner's buckets (revocations, asset_returns, reassignments)."""
    data = plan_data or {}
    if "actions" in data:
        return list(data.get("actions") or [])
    return [
        *(data.get("revocations") or []),
        *(data.get("asset_returns") or []),
        *(data.get("reassignments") or []),
    ]


def _structured_revision_diff(parent: CasePlan, revised: CasePlan) -> dict:
    # Keyed by resource, so "REASSIGN credential -> DOWNSCOPE credential"
    # reads as one changed step, which is the correction the lesson is about.
    before = {
        item["resource_key"]: item
        for item in map(_normalized_action, _plan_actions(parent.plan_data))
    }
    after = {
        item["resource_key"]: item
        for item in map(_normalized_action, _plan_actions(revised.plan_data))
    }

    added = [after[key] for key in sorted(after.keys() - before.keys())]
    removed = [before[key] for key in sorted(before.keys() - after.keys())]
    changed = [
        {"before": before[key], "after": after[key]}
        for key in sorted(before.keys() & after.keys())
        if before[key] != after[key]
    ]

    return {"added": added, "removed": removed, "changed": changed}


def _sanitize_candidate_text(text: str, db: Session, case: Case) -> str:
    value = text
    subject = db.get(Person, case.subject_person_id)
    if subject and subject.name:
        value = re.sub(re.escape(subject.name), "[EMPLOYEE]", value, flags=re.I)

    resources = list(
        db.scalars(
            select(CompanyResource).where(
                CompanyResource.person_id == case.subject_person_id
            )
        )
    )
    for resource in resources:
        if resource.resource_key:
            value = value.replace(resource.resource_key, "[RESOURCE]")

    value = _SECRET_RE.sub("[REDACTED]", value)
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _UUID_RE.sub("[REDACTED_ID]", value)
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return re.sub(r"[ \t]+", " ", value).strip()


def _candidate_memory_text(candidate: LearningCandidate) -> str:
    parts = [
        f"Situation: {candidate.situation}",
        f"Recommended action: {candidate.recommended_action}",
        f"Rationale: {candidate.rationale}",
    ]
    if candidate.conditions:
        parts.append("Conditions: " + " | ".join(candidate.conditions))
    return "\n".join(parts)


def _policy_evidence_for_plan(
    db: Session, plan: CasePlan
) -> tuple[list[PolicyVersion], list[str]]:
    links = list(
        db.scalars(
            select(PolicyLink).where(
                PolicyLink.subject_type == PolicyLinkSubjectType.PLAN,
                PolicyLink.subject_id == plan.id,
            )
        )
    )
    if not links:
        raise LearningConflictError("The revised plan has no policy links.")

    policies: list[PolicyVersion] = []
    evidence_ids: list[str] = []
    for link in links:
        policy = db.get(PolicyVersion, link.policy_version_id)
        if policy is None or policy.status != PolicyState.CURRENT:
            raise LearningConflictError(
                "A policy used by the revised plan is no longer CURRENT."
            )
        policies.append(policy)
        evidence_ids.extend(str(item) for item in (link.evidence_ids or []))
    # Links come back in no fixed order; a stable order keeps the lesson
    # prompt identical between runs, so the demo cache can answer it.
    policies.sort(key=lambda policy: (policy.policy_code, policy.version_number))
    return policies, sorted(set(evidence_ids))


def _validate_learning_reviewer(db: Session, assigned_to: UUID) -> Person:
    reviewer = db.get(Person, assigned_to)
    if reviewer is None:
        raise LearningNotFoundError(f"Learning reviewer does not exist: {assigned_to}")
    if reviewer.app_role not in {AppRole.IT_OWNER, AppRole.ADMIN}:
        raise LearningConflictError(
            "PLAN_CORRECTION access learning must be approved by an IT owner or admin."
        )
    return reviewer


def create_plan_correction_candidate(
    db: Session,
    case_id: UUID,
    assigned_to: UUID,
) -> tuple[LearningRecord, Approval, LearningCandidate, bool]:
    case = db.get(Case, case_id)
    if case is None:
        raise LearningNotFoundError(f"Case does not exist: {case_id}")
    if case.status != CaseState.COMPLETED:
        raise LearningConflictError(
            f"Source case must be COMPLETED. Current status: {case.status.value}"
        )

    revised = db.scalar(
        select(CasePlan)
        .where(
            CasePlan.case_id == case.id,
            CasePlan.parent_plan_id.is_not(None),
            CasePlan.status == PlanState.APPROVED,
        )
        .order_by(CasePlan.revision.desc())
        .limit(1)
    )
    if revised is None or revised.parent_plan_id is None:
        raise LearningConflictError(
            "The completed case has no approved manager revision to learn from."
        )
    parent = db.get(CasePlan, revised.parent_plan_id)
    if parent is None:
        raise LearningConflictError("The parent AI plan no longer exists.")

    unverified = list(
        db.scalars(
            select(CaseAction).where(
                CaseAction.plan_id == revised.id,
                CaseAction.status != ActionState.VERIFIED,
            )
        )
    )
    if unverified:
        raise LearningConflictError(
            "Every action in the revised plan must be VERIFIED before learning."
        )

    existing = db.scalar(
        select(LearningRecord).where(
            LearningRecord.source_case_id == case.id,
            LearningRecord.trigger_type == LearningTriggerType.PLAN_CORRECTION,
            LearningRecord.status.in_(
                [
                    LearningState.PENDING_APPROVAL,
                    LearningState.APPROVED,
                ]
            ),
        )
    )
    if existing is not None:
        raise LearningConflictError(
            f"This correction already has a {existing.status.value} learning record: {existing.id}"
        )

    diff = _structured_revision_diff(parent, revised)
    if not diff["added"] and not diff["removed"] and not diff["changed"]:
        raise LearningConflictError("NO_REUSABLE_CORRECTION")

    policies, evidence_ids = _policy_evidence_for_plan(db, revised)
    reviewer = _validate_learning_reviewer(db, assigned_to)
    subject = db.get(Person, case.subject_person_id)
    if subject is None:
        raise LearningNotFoundError("Case subject does not exist.")

    scope = {
        "case_types": [case.case_type.value],
        "departments": [subject.department],
        "roles": [subject.job_title],
        "sensitivity": str((case.case_facts or {}).get("sensitivity") or "INTERNAL"),
    }
    policy_payload = [
        {
            "policy_version_id": str(policy.id),
            "policy_code": policy.policy_code,
            "version_number": policy.version_number,
            "text": policy.content_text[:6000],
        }
        for policy in policies
    ]

    sanitized = generate_learning_candidate_via_graph(
        case_id=case.id,
        case_facts=dict(case.case_facts or {}),
        correction_summary=revised.correction_summary or "",
        structured_diff=diff,
        policy_payload=policy_payload,
        scope=scope,
        policy_refs=[str(policy.id) for policy in policies],
        source_evidence=evidence_ids,
        sanitize_text=lambda text: _sanitize_candidate_text(
            text,
            db,
            case,
        ),
    )
    sanitized.sensitive_data_removed = True

    memory_text = _sanitize_candidate_text(_candidate_memory_text(sanitized), db, case)
    canonical_scope = _canonical_scope(scope)
    content_hash = hashlib.sha256(
        (memory_text + "\n" + canonical_scope).encode("utf-8")
    ).hexdigest()

    duplicate = db.scalar(
        select(LearningRecord).where(
            LearningRecord.content_hash == content_hash,
            LearningRecord.status.in_(
                [
                    LearningState.PENDING_APPROVAL,
                    LearningState.APPROVED,
                ]
            ),
        )
    )
    if duplicate is not None:
        raise LearningConflictError(
            f"An identical learning record already exists: {duplicate.id}"
        )

    duplicate_warning = False
    try:
        nearby = search_learning_memory(
            query=memory_text,
            case_type=case.case_type.value,
            department=subject.department,
            role=subject.job_title,
            sensitivity=scope["sensitivity"],
            top_k=1,
        )
        duplicate_warning = bool(nearby and nearby[0].score > 0.92)
    except Exception:
        duplicate_warning = False

    record = LearningRecord(
        source_case_id=case.id,
        source_plan_id=revised.id,
        trigger_type=LearningTriggerType.PLAN_CORRECTION,
        status=LearningState.PENDING_APPROVAL,
        candidate_data=jsonable_encoder(
            {
                "candidate": sanitized.model_dump(),
                "revision_diff": diff,
                "parent_plan_id": str(parent.id),
                "revised_plan_id": str(revised.id),
                "duplicate_warning": duplicate_warning,
            }
        ),
        memory_text=memory_text,
        scope=scope,
        qdrant_point_id=None,
        stale_reason=None,
        content_hash=content_hash,
    )
    db.add(record)
    db.flush()

    approval = Approval(
        target_type=ApprovalTargetType.LEARNING,
        target_id=record.id,
        requested_by=case.created_by_id,
        assigned_to=reviewer.id,
        status=ApprovalState.PENDING,
    )
    db.add(approval)
    db.flush()

    record_audit_event(
        db,
        actor_type=AuditActorType.LLM,
        event_type="LEARNING_CANDIDATE_CREATED",
        entity_type="learning_record",
        entity_id=record.id,
        after_data={
            "status": record.status.value,
            "trigger_type": record.trigger_type.value,
            "duplicate_warning": duplicate_warning,
        },
        evidence_data={
            "parent_plan_id": str(parent.id),
            "revised_plan_id": str(revised.id),
            "policy_version_ids": [str(policy.id) for policy in policies],
        },
        correlation_id=case.id,
    )
    db.commit()
    db.refresh(record)
    db.refresh(approval)
    return record, approval, sanitized, duplicate_warning


def decide_learning_candidate(
    db: Session,
    approval_id: UUID,
    decided_by: UUID,
    decision: ApprovalState,
    comment: str | None,
) -> tuple[Approval, LearningRecord]:
    if decision not in {ApprovalState.APPROVED, ApprovalState.REJECTED}:
        raise LearningConflictError("Decision must be APPROVED or REJECTED.")
    if decision == ApprovalState.REJECTED and not (comment and comment.strip()):
        raise LearningConflictError("A rejection comment is required.")

    approval = db.get(Approval, approval_id)
    if approval is None:
        raise LearningNotFoundError(f"Approval does not exist: {approval_id}")
    if approval.target_type != ApprovalTargetType.LEARNING:
        raise LearningConflictError(
            "This approval does not target a learning candidate."
        )
    if approval.status != ApprovalState.PENDING:
        raise LearningConflictError(
            f"Learning approval already decided: {approval.status.value}"
        )
    if approval.assigned_to != decided_by:
        raise LearningConflictError(
            "Only the assigned reviewer can decide this candidate."
        )

    record = db.get(LearningRecord, approval.target_id)
    if record is None:
        raise LearningNotFoundError(
            f"Learning record does not exist: {approval.target_id}"
        )
    if record.status != LearningState.PENDING_APPROVAL:
        raise LearningConflictError(
            f"Learning record is not awaiting approval: {record.status.value}"
        )

    _validate_source_ready(db, record)
    _copy_current_policy_links(db, record)

    approval.status = decision
    approval.comment = comment
    approval.decided_at = datetime.now(timezone.utc)
    record.status = (
        LearningState.APPROVED
        if decision == ApprovalState.APPROVED
        else LearningState.REJECTED
    )

    record_audit_event(
        db,
        actor_type=AuditActorType.USER,
        actor_id=decided_by,
        event_type=(
            "LEARNING_APPROVED"
            if decision == ApprovalState.APPROVED
            else "LEARNING_REJECTED"
        ),
        entity_type="learning_record",
        entity_id=record.id,
        before_data={"status": LearningState.PENDING_APPROVAL.value},
        after_data={"status": record.status.value, "comment": comment},
        correlation_id=record.source_case_id,
    )
    db.commit()
    db.refresh(approval)
    db.refresh(record)

    if decision == ApprovalState.APPROVED:
        record, _, _, _ = index_approved_learning(db, record.id)

    return approval, record
