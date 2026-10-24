"""Rebuild the Qdrant policy index from the policy text stored in PostgreSQL.

Used when the Qdrant collection is lost (e.g. a deleted free cluster). For
each seed policy code it re-indexes V1 from `policy_versions.content_text`,
after checking that text against the stored content hash, so Qdrant holds
exactly what the database says was approved. Policy status is never changed;
`reset_policies` does that. Chunk point IDs are deterministic, so running
this again only overwrites the same points.

Run: python -m app.scripts.reindex_policies [--yes]
"""
from __future__ import annotations

import argparse
import hashlib
from collections.abc import Iterable

from sqlalchemy import select

from app.database import SessionLocal
from app.models import PolicyVersion
from app.scripts.reset_policies import SEED_POLICY_CODES, SEED_VERSION


class PolicyReindexError(RuntimeError):
    pass


def select_versions_to_reindex(
    versions: Iterable[PolicyVersion],
    codes: Iterable[str] = SEED_POLICY_CODES,
) -> list[PolicyVersion]:
    """Seed V1 of every given code that exists, in code order."""
    wanted = list(codes)
    selected = [
        version
        for version in versions
        if version.policy_code in wanted and version.version_number == SEED_VERSION
    ]
    return sorted(selected, key=lambda version: wanted.index(version.policy_code))


def verify_content_hash(version: PolicyVersion) -> None:
    actual = hashlib.sha256(version.content_text.encode("utf-8")).hexdigest()
    if actual != version.content_hash:
        raise PolicyReindexError(
            f"{version.policy_code} V{version.version_number}: stored text does "
            "not match its content hash; refusing to index it."
        )


def reindex_policy_version(version: PolicyVersion) -> tuple[int, int]:
    """Index one version; returns (expected chunks, points now in Qdrant)."""
    from app.rag.policy_chunks import build_policy_chunks
    from app.rag.policy_loader import split_policy_text
    from app.rag.policy_vector_store import count_policy_chunks, store_policy_chunks

    verify_content_hash(version)
    chunks = build_policy_chunks(
        split_policy_text(version.content_text),
        policy_version_id=version.id,
        policy_code=version.policy_code,
        version_number=version.version_number,
        title=version.title,
        department=version.department,
        document_text=version.content_text,
    )
    store_policy_chunks(chunks)
    return len(chunks), count_policy_chunks(version.id)


def main() -> None:
    from app.rag.qdrant_collections import (
        ensure_policy_collection,
        ensure_policy_version_index,
    )

    parser = argparse.ArgumentParser(description="Rebuild the Qdrant policy index.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation.")
    args = parser.parse_args()

    with SessionLocal() as db:
        versions = select_versions_to_reindex(db.scalars(select(PolicyVersion)))
        for version in versions:
            # Fail before any write if a stored text was altered.
            verify_content_hash(version)

        print("\nPolicy versions to index:")
        for version in versions:
            print(f"  {version.policy_code} V{version.version_number} ({version.status.value})")
        if not versions:
            print("  none found; ingest the seed policies instead.")
            return

        if not args.yes:
            answer = input("Create the collection if needed and index these? [y/N]: ")
            if answer.strip().lower() not in {"y", "yes"}:
                print("Reindex cancelled.")
                return

        print(ensure_policy_collection())
        print(ensure_policy_version_index())

        for version in versions:
            expected, indexed = reindex_policy_version(version)
            label = f"{version.policy_code} V{version.version_number}"
            if indexed != expected:
                raise PolicyReindexError(
                    f"{label}: expected {expected} points, found {indexed}."
                )
            print(f"  indexed {label}: {indexed} chunks")


if __name__ == "__main__":
    main()
