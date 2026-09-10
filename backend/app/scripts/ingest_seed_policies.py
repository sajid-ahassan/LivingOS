from datetime import date
from pathlib import Path
from uuid import UUID

from app.database import SessionLocal
from app.rag.policy_ingestion import ingest_policy

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_DIRECTORY = PROJECT_ROOT / "data" / "seed"

TAHMID_ID = UUID("33333333-3333-4333-8333-333333333333")


POLICIES = [
    {
        "file_path": SEED_DIRECTORY / "access_policy_v1.md",
        "policy_code": "ACCESS",
        "title": "Access Policy",
        "version_number": 1,
        "department": "GLOBAL",
        "effective_from": date(2026, 10, 1),
    },
    {
        "file_path": SEED_DIRECTORY / "equipment_policy_v1.md",
        "policy_code": "EQUIPMENT",
        "title": "Equipment Policy",
        "version_number": 1,
        "department": "GLOBAL",
        "effective_from": date(2026, 10, 1),
    },
    {
        "file_path": SEED_DIRECTORY / "offboarding_policy_v1.md",
        "policy_code": "OFFBOARDING",
        "title": "Offboarding Policy",
        "version_number": 1,
        "department": "GLOBAL",
        "effective_from": date(2026, 10, 1),
    },
]


def main() -> None:
    with SessionLocal() as db:
        for policy_data in POLICIES:
            result = ingest_policy(
                db,
                uploaded_by=TAHMID_ID,
                **policy_data,
            )

            print()
            print(
                "Policy:",
                f"{result.policy_code} V{result.version_number}",
            )
            print("Policy ID:", result.policy_version_id)
            print("Status:", result.status)
            print("Expected chunks:", result.expected_chunks)
            print("Indexed chunks:", result.indexed_chunks)
            print(
                "Evidence IDs:",
                ", ".join(result.evidence_ids),
            )


if __name__ == "__main__":
    main()
