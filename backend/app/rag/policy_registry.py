import hashlib
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import PolicyState
from app.models import Person, PolicyVersion


def register_policy_draft(
    db: Session,
    *,
    policy_code: str,
    title: str,
    version_number: int,
    department: str,
    effective_from: date,
    content_text: str,
    uploaded_by: UUID,
) -> PolicyVersion:
    policy_code = policy_code.strip().upper()
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

    if db.get(Person, uploaded_by) is None:
        raise ValueError("Policy uploader does not exist.")

    existing = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_code == policy_code,
            PolicyVersion.version_number == version_number,
        )
    )

    if existing:
        if existing.content_hash != content_hash:
            raise ValueError(
                f"{policy_code} V{version_number} already exists "
                "with different content."
            )

        return existing

    policy = PolicyVersion(
        policy_code=policy_code,
        title=title,
        version_number=version_number,
        status=PolicyState.DRAFT,
        department=department,
        effective_from=effective_from,
        content_text=content_text,
        content_hash=content_hash,
        uploaded_by=uploaded_by,
    )

    db.add(policy)

    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        raise

    return policy




def activate_policy(
    db: Session,
    *,
    policy_version_id: UUID,
    expected_chunks: int,
    indexed_chunks: int,
) -> PolicyVersion:
    if expected_chunks < 1:
        raise ValueError("A policy must contain at least one chunk.")

    if indexed_chunks != expected_chunks:
        raise RuntimeError(
            f"Policy activation blocked: expected {expected_chunks} "
            f"chunks but found {indexed_chunks} in Qdrant."
        )

    policy = db.get(PolicyVersion, policy_version_id)

    if policy is None:
        raise ValueError("Policy version does not exist.")

    if policy.status == PolicyState.CURRENT:
        return policy

    if policy.status != PolicyState.DRAFT:
        raise ValueError(
            f"Cannot activate a policy with status {policy.status.value}."
        )

    another_current = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_code == policy.policy_code,
            PolicyVersion.status == PolicyState.CURRENT,
            PolicyVersion.id != policy.id,
        )
    )

    if another_current:
        raise ValueError(
            f"{policy.policy_code} already has a CURRENT version. "
            "A policy-change approval is required."
        )

    policy.status = PolicyState.CURRENT

    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        raise

    return policy