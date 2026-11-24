"""Approved lessons as advisory context for the planners.

A lesson is a reviewer-approved, sanitized manager correction. Planners may
read lessons, but they rank below policy: every plan step must still cite
policy evidence, and a lesson ID (MEM-<learning id>-C0) is only accepted next
to it. Only lessons that are APPROVED, not stale, indexed, and linked to
policy versions that are still CURRENT reach a planner, so a lesson made
under an old rule can never steer a new plan.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import LearningState, PolicyLinkSubjectType, PolicyState
from app.models import LearningRecord, PolicyLink, PolicyVersion


logger = logging.getLogger(__name__)

LESSON_EVIDENCE = re.compile(r"^MEM-(?P<learning_id>[0-9a-fA-F-]{36})-C\d+$")

# Cosine similarity below this is treated as unrelated.
LESSON_MIN_SCORE = 0.30
LESSON_TOP_K = 3


@dataclass(frozen=True)
class LessonContext:
    evidence_id: str
    learning_id: UUID
    text: str
    # What the manager's correction did to a reassigned agent's credential,
    # read from the stored revision diff ("read" for a read-only DOWNSCOPE).
    # The planner only decides whether the lesson applies; this recorded
    # change is then applied by rule, not by the model.
    credential_permission: str | None = None


def credential_permission_from_diff(revision_diff: dict | None) -> str | None:
    """The permission a correction gave a reassigned agent's credential."""
    diff = revision_diff or {}
    after = [
        *(diff.get("added") or []),
        *((item or {}).get("after") or {} for item in diff.get("changed") or []),
    ]
    for action in after:
        if (
            action.get("resource_type") == "AGENT_CREDENTIAL"
            and action.get("action_type") == "DOWNSCOPE"
        ):
            permission = (action.get("requested_data") or {}).get("permission")
            if permission:
                return str(permission)
    return None


def is_lesson_evidence(evidence_id: str) -> bool:
    return bool(LESSON_EVIDENCE.match(str(evidence_id)))


def lesson_ids_in(evidence_ids: Iterable[str]) -> set[str]:
    return {item for item in evidence_ids if is_lesson_evidence(item)}


def _learning_id(evidence_id: str) -> UUID | None:
    match = LESSON_EVIDENCE.match(str(evidence_id))
    return UUID(match["learning_id"]) if match else None


def lesson_is_usable(db: Session, record: LearningRecord | None) -> bool:
    """APPROVED, not stale, indexed, and every linked policy still CURRENT."""
    if record is None:
        return False
    if record.status != LearningState.APPROVED or record.stale_reason:
        return False
    if record.qdrant_point_id is None:
        return False
    statuses = list(
        db.scalars(
            select(PolicyVersion.status)
            .join(PolicyLink, PolicyLink.policy_version_id == PolicyVersion.id)
            .where(
                PolicyLink.subject_type == PolicyLinkSubjectType.LEARNING,
                PolicyLink.subject_id == record.id,
            )
        )
    )
    return all(status == PolicyState.CURRENT for status in statuses)


def usable_lesson_ids(db: Session, evidence_ids: Iterable[str]) -> set[str]:
    """The lesson IDs among evidence_ids that may still be cited."""
    usable = set()
    for evidence_id in lesson_ids_in(evidence_ids):
        learning_id = _learning_id(evidence_id)
        if learning_id and lesson_is_usable(db, db.get(LearningRecord, learning_id)):
            usable.add(evidence_id)
    return usable


def offboarding_lesson_query(department: str, job_title: str, resources) -> str:
    """Deterministic search text, so demo caches hit across runs."""
    agents = sorted(
        f"{(r.details_data or {}).get('agent_name')}: {(r.details_data or {}).get('purpose')}"
        for r in resources
        if r.resource_type.value == "AI_AGENT"
    )
    parts = [f"Offboarding a departing {job_title} in {department}"]
    if agents:
        parts.append("Sponsored AI agents: " + "; ".join(agents))
    return ". ".join(parts)


def retrieve_offboarding_lessons(
    db: Session,
    *,
    department: str,
    job_title: str,
    resources,
) -> list[LessonContext]:
    """Approved lessons relevant to this offboarding, re-checked in PostgreSQL.

    The vector store only proposes candidates; PostgreSQL decides. A failure
    here never blocks planning: lessons are advisory, so the planner then
    works from policy alone.
    """
    from app.rag.learning_memory import search_learning_memory

    try:
        hits = search_learning_memory(
            query=offboarding_lesson_query(department, job_title, resources),
            case_type="OFFBOARDING",
            department=department,
            top_k=LESSON_TOP_K,
        )
    except Exception as exc:  # noqa: BLE001 - advisory context only
        logger.warning("Lesson retrieval skipped: %s", exc)
        return []

    lessons: list[LessonContext] = []
    for hit in hits:
        if hit.score < LESSON_MIN_SCORE or not hit.text.strip():
            continue
        record = db.get(LearningRecord, hit.learning_id)
        if not lesson_is_usable(db, record):
            continue
        lessons.append(
            LessonContext(
                evidence_id=hit.evidence_id or f"MEM-{hit.learning_id}-C0",
                learning_id=hit.learning_id,
                text=hit.text.strip(),
                credential_permission=credential_permission_from_diff(
                    (record.candidate_data or {}).get("revision_diff")
                ),
            )
        )
    return sorted(lessons, key=lambda item: item.evidence_id)


def format_lessons(lessons: list[LessonContext]) -> str:
    if not lessons:
        return "No approved lessons apply to this case."
    return "\n\n".join(
        f"Lesson ID: {lesson.evidence_id}\nLesson: {lesson.text}"
        + (
            "\nRecorded correction: a reassigned agent's credential becomes "
            f"{lesson.credential_permission}-only. LivingOps applies this when you "
            "REASSIGN the agent and cite this lesson ID on that step."
            if lesson.credential_permission
            else ""
        )
        for lesson in lessons
    )
