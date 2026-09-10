from datetime import date
from pathlib import Path
from uuid import UUID

from app.database import SessionLocal
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


PROJECT_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = (
    PROJECT_ROOT
    / "data"
    / "seed"
    / "access_policy_v1.md"
)

TAHMID_ID = UUID(
    "33333333-3333-4333-8333-333333333333"
)


def main() -> None:
    policy_text = load_policy_text(POLICY_PATH)

    with SessionLocal() as db:
        policy = register_policy_draft(
            db,
            policy_code="ACCESS",
            title="Access Policy",
            version_number=1,
            department="GLOBAL",
            effective_from=date(2026, 10, 1),
            content_text=policy_text,
            uploaded_by=TAHMID_ID,
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

        stored_count = store_policy_chunks(policy_chunks)
        indexed_count = count_policy_chunks(policy.id)

        previous_status = policy.status.value

        policy = activate_policy(
            db,
            policy_version_id=policy.id,
            expected_chunks=len(policy_chunks),
            indexed_chunks=indexed_count,
        )

        print("Policy ID:", policy.id)
        print(
            "Policy:",
            f"{policy.policy_code} V{policy.version_number}",
        )
        print(
            "Status:",
            f"{previous_status} -> {policy.status.value}",
        )
        print("Content hash:", policy.content_hash)
        print("Chunks created:", len(text_chunks))
        print("Qdrant points stored:", stored_count)
        print("Qdrant points verified:", indexed_count)

        for chunk in policy_chunks:
            print("Evidence ID:", chunk.evidence_id)


if __name__ == "__main__":
    main()