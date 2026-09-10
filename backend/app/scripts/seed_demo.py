from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import AppRole, EmploymentStatus, ResourceState, ResourceType
from app.models import CompanyResource, Person


PEOPLE = [
    {
        "id": UUID("11111111-1111-4111-8111-111111111111"),
        "name": "Farhana Islam",
        "email": "farhana.islam@nexora.demo",
        "app_role": AppRole.HR_MANAGER,
        "employment_status": EmploymentStatus.ACTIVE,
        "department": "PEOPLE",
        "job_title": "HR Manager",
        "manager_id": None,
    },
    {
        "id": UUID("22222222-2222-4222-8222-222222222222"),
        "name": "Nabil Chowdhury",
        "email": "nabil.chowdhury@nexora.demo",
        "app_role": AppRole.LINE_MANAGER,
        "employment_status": EmploymentStatus.ACTIVE,
        "department": "ENGINEERING",
        "job_title": "Engineering Manager",
        "manager_id": None,
    },
    {
        "id": UUID("33333333-3333-4333-8333-333333333333"),
        "name": "Tahmid Hasan",
        "email": "tahmid.hasan@nexora.demo",
        "app_role": AppRole.IT_OWNER,
        "employment_status": EmploymentStatus.ACTIVE,
        "department": "IT_SECURITY",
        "job_title": "IT Security Owner",
        "manager_id": None,
    },
    {
        "id": UUID("44444444-4444-4444-8444-444444444444"),
        "name": "Amina Rahman",
        "email": "amina.rahman@nexora.demo",
        "app_role": AppRole.EMPLOYEE,
        "employment_status": EmploymentStatus.CANDIDATE,
        "department": "ENGINEERING",
        "job_title": "AI Engineer",
        "manager_id": UUID("22222222-2222-4222-8222-222222222222"),
    },
    {
        "id": UUID("55555555-5555-4555-8555-555555555555"),
        "name": "Rafi Ahmed",
        "email": "rafi.ahmed@nexora.demo",
        "app_role": AppRole.EMPLOYEE,
        "employment_status": EmploymentStatus.CANDIDATE,
        "department": "ENGINEERING",
        "job_title": "AI Engineer",
        "manager_id": UUID("22222222-2222-4222-8222-222222222222"),
    },
    {
        "id": UUID("66666666-6666-4666-8666-666666666666"),
        "name": "Arif Hossain",
        "email": "arif.hossain@nexora.demo",
        "app_role": AppRole.EMPLOYEE,
        "employment_status": EmploymentStatus.DEPARTING,
        "department": "ENGINEERING",
        "job_title": "Senior Software Engineer",
        "manager_id": UUID("22222222-2222-4222-8222-222222222222"),
    },
]


ARIF_ID = UUID("66666666-6666-4666-8666-666666666666")


RESOURCES = [
    {
        "resource_type": ResourceType.EMAIL_ACCOUNT,
        "resource_key": "email:arif.hossain@nexora.demo",
        "status": ResourceState.ACTIVE,
        "details_data": {"address": "arif.hossain@nexora.demo"},
        "idempotency_key": "seed:arif:email",
    },
    {
        "resource_type": ResourceType.GITHUB_ACCESS,
        "resource_key": "github:aurora:arif",
        "status": ResourceState.ACTIVE,
        "details_data": {"project": "AURORA", "access_level": "WRITE"},
        "idempotency_key": "seed:arif:github-aurora-write",
    },
    {
        "resource_type": ResourceType.LAPTOP,
        "resource_key": "LAPTOP-ARIF-01",
        "status": ResourceState.ASSIGNED,
        "details_data": {"catalog_key": "LAPTOP-ENG", "asset_tag": "LAPTOP-ARIF-01"},
        "idempotency_key": "seed:arif:laptop",
    },
    {
        "resource_type": ResourceType.WORK_ITEM,
        "resource_key": "WORK-AURORA-API",
        "status": ResourceState.OPEN,
        "details_data": {"title": "Aurora API integration", "project": "AURORA"},
        "idempotency_key": "seed:arif:work-aurora-api",
    },
    {
        "resource_type": ResourceType.KNOWLEDGE_DOCUMENT,
        "resource_key": "DOC-AURORA-RUNBOOK",
        "status": ResourceState.ACTIVE,
        "details_data": {"title": "Aurora Operations Runbook", "project": "AURORA"},
        "idempotency_key": "seed:arif:aurora-runbook",
    },
]


def upsert_people(db: Session) -> None:
    for values in PEOPLE:
        person = db.get(Person, values["id"])
        if person is None:
            db.add(Person(**values))
            continue

        for field, value in values.items():
            if field != "id":
                setattr(person, field, value)

    db.flush()


def upsert_resources(db: Session) -> None:
    for values in RESOURCES:
        resource = db.scalar(
            select(CompanyResource).where(
                CompanyResource.resource_key == values["resource_key"]
            )
        )

        if resource is None:
            db.add(CompanyResource(person_id=ARIF_ID, **values))
            continue

        resource.person_id = ARIF_ID
        resource.source_action_id = None
        for field, value in values.items():
            setattr(resource, field, value)


def main() -> None:
    with SessionLocal() as db:
        try:
            upsert_people(db)
            upsert_resources(db)
            db.commit()
        except Exception:
            db.rollback()
            raise

    print(f"Seeded {len(PEOPLE)} people and {len(RESOURCES)} resources.")


if __name__ == "__main__":
    main()
