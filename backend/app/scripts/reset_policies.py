"""Controlled policy reset: bring every seed policy back to its V1.

The demo story starts on Access Policy V1 and activates V2 in scene 6, and the
Guardian only accepts version current+1. After a rehearsal (or old test runs)
a later version is CURRENT, so this script, for each seed policy code:

1. checks that V1 still has its Qdrant points (otherwise it stops, unchanged),
2. deletes the later versions with their policy changes, impacts, impact
   approvals and policy links,
3. makes V1 CURRENT again,
4. after the database commit, deletes the later versions' Qdrant points.

Policy rows are never deleted without cleaning their Qdrant points.

Run: python -m app.scripts.reset_policies [--yes]
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import ApprovalTargetType, PolicyState
from app.models import (
    Approval,
    PolicyChange,
    PolicyImpact,
    PolicyLink,
    PolicyVersion,
)


SEED_POLICY_CODES = ("ACCESS", "EQUIPMENT", "OFFBOARDING", "AGENT")
SEED_VERSION = 1


class PolicyResetError(RuntimeError):
    pass


@dataclass(frozen=True)
class PolicyVersionRow:
    id: UUID
    policy_code: str
    version_number: int
    status: PolicyState


@dataclass
class PolicyResetPlan:
    remove: list[PolicyVersionRow] = field(default_factory=list)
    restore: list[PolicyVersionRow] = field(default_factory=list)
    keep: list[PolicyVersionRow] = field(default_factory=list)
    not_ingested: list[str] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        return not self.remove and not self.restore


def plan_policy_reset(
    versions: Iterable[PolicyVersionRow],
    codes: Iterable[str] = SEED_POLICY_CODES,
) -> PolicyResetPlan:
    """Decide what to remove and restore; touches nothing."""
    plan = PolicyResetPlan()
    by_code: dict[str, list[PolicyVersionRow]] = {}
    for row in versions:
        by_code.setdefault(row.policy_code, []).append(row)

    for code in codes:
        rows = sorted(by_code.get(code, []), key=lambda row: row.version_number)
        if not rows:
            plan.not_ingested.append(code)
            continue
        seed = [row for row in rows if row.version_number == SEED_VERSION]
        if not seed:
            raise PolicyResetError(
                f"{code} has no V{SEED_VERSION}; ingest the seed policy first."
            )
        plan.remove.extend(row for row in rows if row.version_number != SEED_VERSION)
        if seed[0].status == PolicyState.CURRENT:
            plan.keep.append(seed[0])
        else:
            plan.restore.append(seed[0])
    return plan


def _load_versions(db: Session) -> list[PolicyVersionRow]:
    return [
        PolicyVersionRow(
            id=version.id,
            policy_code=version.policy_code,
            version_number=version.version_number,
            status=version.status,
        )
        for version in db.scalars(select(PolicyVersion))
    ]


def apply_policy_reset(
    db: Session,
    plan: PolicyResetPlan,
    *,
    count_points: Callable[[UUID], int],
) -> dict[str, int]:
    """Database part of the reset. The caller commits, then cleans Qdrant."""
    for row in [*plan.restore, *plan.keep]:
        if count_points(row.id) < 1:
            raise PolicyResetError(
                f"{row.policy_code} V{row.version_number} has no Qdrant points; "
                "re-ingest it before resetting. Nothing was changed."
            )

    counts = {
        "policy_versions": 0,
        "policy_changes": 0,
        "policy_impacts": 0,
        "impact_approvals": 0,
        "policy_links": 0,
        "restored_v1": len(plan.restore),
    }
    remove_ids = [row.id for row in plan.remove]

    if remove_ids:
        change_ids = list(
            db.scalars(
                select(PolicyChange.id).where(
                    or_(
                        PolicyChange.old_version_id.in_(remove_ids),
                        PolicyChange.new_version_id.in_(remove_ids),
                    )
                )
            )
        )
        impact_ids = (
            list(
                db.scalars(
                    select(PolicyImpact.id).where(
                        PolicyImpact.policy_change_id.in_(change_ids)
                    )
                )
            )
            if change_ids
            else []
        )
        if impact_ids:
            counts["impact_approvals"] = db.execute(
                delete(Approval).where(
                    Approval.target_type == ApprovalTargetType.POLICY_IMPACT,
                    Approval.target_id.in_(impact_ids),
                )
            ).rowcount or 0
            counts["policy_impacts"] = db.execute(
                delete(PolicyImpact).where(PolicyImpact.id.in_(impact_ids))
            ).rowcount or 0
        if change_ids:
            counts["policy_changes"] = db.execute(
                delete(PolicyChange).where(PolicyChange.id.in_(change_ids))
            ).rowcount or 0
        counts["policy_links"] = db.execute(
            delete(PolicyLink).where(PolicyLink.policy_version_id.in_(remove_ids))
        ).rowcount or 0
        counts["policy_versions"] = db.execute(
            delete(PolicyVersion).where(PolicyVersion.id.in_(remove_ids))
        ).rowcount or 0
        # The one-CURRENT-per-code index must see the old CURRENT gone first.
        db.flush()

    for row in plan.restore:
        version = db.get(PolicyVersion, row.id)
        version.status = PolicyState.CURRENT
    db.flush()
    return counts


def reset_seed_policies() -> tuple[PolicyResetPlan, dict[str, int]]:
    """Run the full reset in its own transaction, then clean Qdrant."""
    from app.rag.policy_vector_store import count_policy_chunks, delete_policy_chunks

    with SessionLocal() as db:
        try:
            plan = plan_policy_reset(_load_versions(db))
            counts = apply_policy_reset(db, plan, count_points=count_policy_chunks)
            db.commit()
        except Exception:
            db.rollback()
            raise

    # After the commit: if Qdrant fails here, the leftover points belong to
    # versions that no longer exist and are never retrieved (retrieval filters
    # by CURRENT version ids), so the demo still works; rerun to clean them.
    for row in plan.remove:
        delete_policy_chunks(row.id)
    counts["qdrant_versions_cleaned"] = len(plan.remove)
    return plan, counts


def _describe(plan: PolicyResetPlan) -> None:
    for row in plan.remove:
        print(f"  remove  {row.policy_code} V{row.version_number} ({row.status.value})")
    for row in plan.restore:
        print(f"  restore {row.policy_code} V{row.version_number} -> CURRENT")
    for row in plan.keep:
        print(f"  keep    {row.policy_code} V{row.version_number} (CURRENT)")
    for code in plan.not_ingested:
        print(f"  skip    {code} (not ingested yet)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset seed policies to V1.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation.")
    args = parser.parse_args()

    with SessionLocal() as db:
        plan = plan_policy_reset(_load_versions(db))

    print("\nPolicy reset plan:")
    _describe(plan)
    if plan.is_noop:
        print("Nothing to reset.")
        return

    if not args.yes:
        answer = input("Apply this policy reset? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Policy reset cancelled.")
            return

    _, counts = reset_seed_policies()
    for name, count in counts.items():
        print(f"{name:24} {count}")


if __name__ == "__main__":
    main()
