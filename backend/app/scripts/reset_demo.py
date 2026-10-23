from __future__ import annotations

import argparse
from uuid import UUID

from sqlalchemy import delete, or_, select

from app.database import SessionLocal
from app.models import (
    AccessEvent,
    Approval,
    AuditEvent,
    Case,
    CaseAction,
    CasePlan,
    CompanyResource,
    LearningRecord,
    PolicyLink,
)
from app.scripts.seed_demo import PEOPLE, RESOURCES, upsert_people, upsert_resources


DEMO_PERSON_IDS = {item["id"] for item in PEOPLE}


def _collect_demo_ids(db):
    case_ids = set(
        db.scalars(
            select(Case.id).where(
                or_(
                    Case.subject_person_id.in_(DEMO_PERSON_IDS),
                    Case.created_by_id.in_(DEMO_PERSON_IDS),
                )
            )
        )
    )

    plan_ids: set[UUID] = set()
    action_ids: set[UUID] = set()
    learning_ids: set[UUID] = set()

    if case_ids:
        plan_ids = set(
            db.scalars(
                select(CasePlan.id).where(CasePlan.case_id.in_(case_ids))
            )
        )
        action_ids = set(
            db.scalars(
                select(CaseAction.id).where(CaseAction.case_id.in_(case_ids))
            )
        )
        learning_ids = set(
            db.scalars(
                select(LearningRecord.id).where(
                    LearningRecord.source_case_id.in_(case_ids)
                )
            )
        )

    return case_ids, plan_ids, action_ids, learning_ids


def reset_demo_data() -> dict[str, int]:
    """
    Clear deterministic demo transactional data and restore seed people/resources.

    PolicyVersion rows are intentionally preserved because policy versions are
    also represented in Qdrant and should not be reset independently.
    """
    counts: dict[str, int] = {}

    with SessionLocal() as db:
        try:
            case_ids, plan_ids, action_ids, learning_ids = _collect_demo_ids(db)

            linked_target_ids = plan_ids | learning_ids
            if linked_target_ids:
                result = db.execute(
                    delete(PolicyLink).where(
                        PolicyLink.subject_id.in_(linked_target_ids)
                    )
                )
                counts["policy_links"] = result.rowcount or 0
            else:
                counts["policy_links"] = 0

            approval_target_ids = plan_ids | learning_ids
            approval_conditions = [
                Approval.requested_by.in_(DEMO_PERSON_IDS),
                Approval.assigned_to.in_(DEMO_PERSON_IDS),
            ]
            if approval_target_ids:
                approval_conditions.append(
                    Approval.target_id.in_(approval_target_ids)
                )

            result = db.execute(
                delete(Approval).where(or_(*approval_conditions))
            )
            counts["approvals"] = result.rowcount or 0

            if learning_ids:
                result = db.execute(
                    delete(LearningRecord).where(
                        LearningRecord.id.in_(learning_ids)
                    )
                )
                counts["learning_records"] = result.rowcount or 0
            else:
                counts["learning_records"] = 0

            audit_entity_ids = case_ids | plan_ids | action_ids | learning_ids
            audit_conditions = []

            if case_ids:
                audit_conditions.append(
                    AuditEvent.correlation_id.in_(case_ids)
                )

            if audit_entity_ids:
                audit_conditions.append(
                    AuditEvent.entity_id.in_(audit_entity_ids)
                )

            if audit_conditions:
                result = db.execute(
                    delete(AuditEvent).where(or_(*audit_conditions))
                )
                counts["audit_events"] = result.rowcount or 0
            else:
                counts["audit_events"] = 0

            result = db.execute(
                delete(AccessEvent).where(
                    AccessEvent.person_id.in_(DEMO_PERSON_IDS)
                )
            )
            counts["access_events"] = result.rowcount or 0

            result = db.execute(
                delete(CompanyResource).where(
                    CompanyResource.person_id.in_(DEMO_PERSON_IDS)
                )
            )
            counts["company_resources"] = result.rowcount or 0

            if case_ids:
                result = db.execute(
                    delete(Case).where(Case.id.in_(case_ids))
                )
                counts["cases"] = result.rowcount or 0
            else:
                counts["cases"] = 0

            upsert_people(db)
            upsert_resources(db)

            db.commit()

        except Exception:
            db.rollback()
            raise

    return counts


def _print_summary(counts: dict[str, int]) -> None:
    print("\nLivingOps demo reset complete.")
    print("--------------------------------")
    for name, count in counts.items():
        print(f"{name:20} removed: {count}")

    print(f"{'demo_people':20} restored: {len(PEOPLE)}")
    print(f"{'seed_resources':20} restored: {len(RESOURCES)}")
    print("PolicyVersion rows preserved.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset LivingOps deterministic demo data."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation.",
    )
    args = parser.parse_args()

    if not args.yes:
        answer = input(
            "Reset LivingOps demo transactional data? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Reset cancelled.")
            return

    counts = reset_demo_data()
    _print_summary(counts)


if __name__ == "__main__":
    main()
