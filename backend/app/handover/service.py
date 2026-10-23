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

from app.audit.service import record_audit_event
from app.config import get_settings
from app.enums import (
    AppRole,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CaseState,
    CaseType,
    LearningState,
    LearningTriggerType,
    PlanState,
)
from app.handover.prompt import HANDOVER_PROMPT
from app.handover.schemas import HandoverDocument, HandoverGenerateRequest
from app.models import Approval, Case, CasePlan, CompanyResource, LearningRecord, Person


class HandoverError(ValueError):
    pass


class HandoverNotFoundError(HandoverError):
    pass


class HandoverConflictError(HandoverError):
    pass


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.I,
)
_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|api[_ -]?key|secret|token|private[_ -]?key)\b\s*[:=]\s*\S+"
)


def _sanitize_text(value: str) -> tuple[str, bool]:
    text = value.strip()
    original = text
    text = _SECRET_RE.sub("[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _UUID_RE.sub("[REDACTED_ID]", text)
    return text, text != original


def _sanitize_answers(answers: dict[str, str]) -> tuple[dict[str, str], bool]:
    sanitized: dict[str, str] = {}
    changed = False
    for question, answer in answers.items():
        clean_question, q_changed = _sanitize_text(str(question))
        clean_answer, a_changed = _sanitize_text(str(answer))
        if clean_answer:
            sanitized[clean_question[:500]] = clean_answer[:3000]
        changed = changed or q_changed or a_changed
    return sanitized, changed


def _safe_resource_metadata(resource: CompanyResource) -> dict:
    details = dict(resource.details_data or {})
    return {
        "resource_type": resource.resource_type.value,
        "resource_key": resource.resource_key,
        "status": resource.status.value,
        "title": details.get("title"),
        "due_date": details.get("due_date"),
    }


def _latest_approved_plan(db: Session, case_id: UUID) -> CasePlan:
    plan = db.scalar(
        select(CasePlan)
        .where(
            CasePlan.case_id == case_id,
            CasePlan.status == PlanState.APPROVED,
        )
        .order_by(CasePlan.revision.desc())
        .limit(1)
    )
    if plan is None:
        raise HandoverConflictError("The offboarding case has no approved plan.")
    return plan


def _validate_handover_reviewer(db: Session, case: Case, assigned_to: UUID) -> Person:
    reviewer = db.get(Person, assigned_to)
    if reviewer is None:
        raise HandoverNotFoundError(f"Reviewer does not exist: {assigned_to}")
    if reviewer.app_role not in {AppRole.LINE_MANAGER, AppRole.ADMIN}:
        raise HandoverConflictError("Handover review must be assigned to a line manager or admin.")
    if reviewer.id == case.subject_person_id:
        raise HandoverConflictError("The departing employee cannot approve their own handover.")
    return reviewer


def _build_memory_text(document: HandoverDocument) -> str:
    sections: list[str] = [document.summary]
    for heading, values in (
        ("Ongoing work", document.ongoing_work),
        ("Recurring tasks", document.recurring_tasks),
        ("Known issues", document.known_issues),
        ("Key contacts", document.key_contacts),
        ("Undocumented procedures", document.undocumented_procedures),
        ("Successor notes", document.successor_notes),
    ):
        if values:
            sections.append(f"{heading}: " + " | ".join(values))
    return "\n".join(sections)


def generate_handover(
    db: Session,
    case_id: UUID,
    request: HandoverGenerateRequest,
) -> tuple[LearningRecord, Approval, HandoverDocument]:
    case = db.get(Case, case_id)
    if case is None:
        raise HandoverNotFoundError(f"Case does not exist: {case_id}")
    if case.case_type != CaseType.OFFBOARDING:
        raise HandoverConflictError("Handover generation is only available for OFFBOARDING cases.")
    if case.status != CaseState.COMPLETED:
        raise HandoverConflictError(
            f"Offboarding execution must be COMPLETED first. Current status: {case.status.value}"
        )

    existing = db.scalar(
        select(LearningRecord)
        .where(
            LearningRecord.source_case_id == case.id,
            LearningRecord.trigger_type == LearningTriggerType.HANDOVER,
            LearningRecord.status.in_([
                LearningState.PENDING_APPROVAL,
                LearningState.APPROVED,
            ]),
        )
        .limit(1)
    )
    if existing is not None:
        raise HandoverConflictError(
            f"This case already has a {existing.status.value} handover record: {existing.id}"
        )

    plan = _latest_approved_plan(db, case.id)
    reviewer = _validate_handover_reviewer(db, case, request.assigned_to)
    plan_data = dict(plan.plan_data or {})
    targeted_questions = list(plan_data.get("targeted_questions") or [])
    sanitized_answers, deterministic_redaction = _sanitize_answers(request.answers)

    resources = list(
        db.scalars(
            select(CompanyResource)
            .where(CompanyResource.source_action_id.in_([action.id for action in plan.actions]))
            .order_by(CompanyResource.resource_type, CompanyResource.resource_key)
        )
    ) if plan.actions else []

    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    structured_model = model.with_structured_output(HandoverDocument, method="function_calling")
    chain = HANDOVER_PROMPT | structured_model

    result = chain.invoke(
        {
            "plan_data": json.dumps(plan_data, indent=2, default=str),
            "resource_metadata": json.dumps(
                [_safe_resource_metadata(resource) for resource in resources],
                indent=2,
                default=str,
            ),
            "targeted_questions": json.dumps(targeted_questions, indent=2),
            "answers": json.dumps(sanitized_answers, indent=2),
        }
    )
    document = HandoverDocument.model_validate(result)
    if deterministic_redaction and not document.sensitive_data_removed:
        document.sensitive_data_removed = True

    memory_text = _build_memory_text(document)
    memory_text, final_redaction = _sanitize_text(memory_text)
    if final_redaction:
        document.sensitive_data_removed = True

    content_hash = hashlib.sha256(memory_text.encode("utf-8")).hexdigest()
    subject = db.get(Person, case.subject_person_id)
    scope = {
        "case_types": [CaseType.OFFBOARDING.value],
        "departments": [subject.department] if subject else [],
        "roles": [subject.job_title] if subject else [],
        "sensitivity": "INTERNAL",
    }

    record = LearningRecord(
        source_case_id=case.id,
        source_plan_id=plan.id,
        trigger_type=LearningTriggerType.HANDOVER,
        status=LearningState.PENDING_APPROVAL,
        candidate_data=jsonable_encoder({"handover": document.model_dump()}),
        memory_text=memory_text,
        scope=scope,
        qdrant_point_id=None,
        stale_reason=None,
        content_hash=content_hash,
    )
    db.add(record)
    db.flush()

    approval = Approval(
        target_type=ApprovalTargetType.HANDOVER,
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
        event_type="HANDOVER_GENERATED",
        entity_type="learning_record",
        entity_id=record.id,
        after_data={
            "status": record.status.value,
            "approval_id": str(approval.id),
            "sensitive_data_removed": document.sensitive_data_removed,
        },
        evidence_data={"source_plan_id": str(plan.id)},
        correlation_id=case.id,
    )

    db.commit()
    db.refresh(record)
    db.refresh(approval)
    return record, approval, document


def decide_handover(
    db: Session,
    approval_id: UUID,
    decided_by: UUID,
    decision: ApprovalState,
    comment: str | None,
) -> tuple[Approval, LearningRecord]:
    if decision not in {ApprovalState.APPROVED, ApprovalState.REJECTED}:
        raise HandoverConflictError("Decision must be APPROVED or REJECTED.")
    if decision == ApprovalState.REJECTED and not (comment and comment.strip()):
        raise HandoverConflictError("A rejection comment is required.")

    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HandoverNotFoundError(f"Approval does not exist: {approval_id}")
    if approval.target_type != ApprovalTargetType.HANDOVER:
        raise HandoverConflictError("This approval does not target a handover.")
    if approval.status != ApprovalState.PENDING:
        raise HandoverConflictError(
            f"Handover approval has already been decided: {approval.status.value}"
        )
    if approval.assigned_to != decided_by:
        raise HandoverConflictError("Only the assigned reviewer can decide this handover.")

    record = db.get(LearningRecord, approval.target_id)
    if record is None:
        raise HandoverNotFoundError(f"Handover record does not exist: {approval.target_id}")
    if record.status != LearningState.PENDING_APPROVAL:
        raise HandoverConflictError(
            f"Handover record is not awaiting approval: {record.status.value}"
        )

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
        event_type=("HANDOVER_APPROVED" if decision == ApprovalState.APPROVED else "HANDOVER_REJECTED"),
        entity_type="learning_record",
        entity_id=record.id,
        before_data={"status": LearningState.PENDING_APPROVAL.value},
        after_data={"status": record.status.value, "comment": comment},
        evidence_data={
            "approval_id": str(approval.id),
            "qdrant_indexed": False,
            "next_stage": "Stage 2.6 indexes approved learning only",
        },
        correlation_id=record.source_case_id,
    )

    db.commit()
    db.refresh(approval)
    db.refresh(record)
    return approval, record
