from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.rag.policy_chunks import build_policy_chunks
from app.rag.policy_loader import (
    load_policy_text,
    split_policy_text,
)
from app.rag.policy_registry import (
    activate_policy,
    register_policy_draft,
)
from app.rag.policy_vector_store import (
    count_policy_chunks,
    store_policy_chunks,
)


@dataclass
class PolicyIngestionResult:
    policy_version_id: UUID
    policy_code: str
    version_number: int
    status: str
    expected_chunks: int
    indexed_chunks: int
    evidence_ids: list[str]


def ingest_policy(
    db: Session,
    *,
    file_path: Path,
    policy_code: str,
    title: str,
    version_number: int,
    department: str,
    effective_from: date,
    uploaded_by: UUID,
) -> PolicyIngestionResult:
    policy_text = load_policy_text(file_path)

    policy = register_policy_draft(
        db,
        policy_code=policy_code,
        title=title,
        version_number=version_number,
        department=department,
        effective_from=effective_from,
        content_text=policy_text,
        uploaded_by=uploaded_by,
    )

    text_chunks = split_policy_text(policy_text)

    policy_chunks = build_policy_chunks(
        text_chunks,
        policy_version_id=policy.id,
        policy_code=policy.policy_code,
        version_number=policy.version_number,
        title=policy.title,
        department=policy.department,
        document_text=policy_text,
    )

    store_policy_chunks(policy_chunks)
    indexed_count = count_policy_chunks(policy.id)

    policy = activate_policy(
        db,
        policy_version_id=policy.id,
        expected_chunks=len(policy_chunks),
        indexed_chunks=indexed_count,
    )

    return PolicyIngestionResult(
        policy_version_id=policy.id,
        policy_code=policy.policy_code,
        version_number=policy.version_number,
        status=policy.status.value,
        expected_chunks=len(policy_chunks),
        indexed_chunks=indexed_count,
        evidence_ids=[chunk.evidence_id for chunk in policy_chunks],
    )
