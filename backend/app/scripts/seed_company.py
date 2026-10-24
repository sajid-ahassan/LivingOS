"""Seed the fictional Nexora Labs company around the six story characters.

Everything here is generated from a fixed random seed and uuid5 IDs, so every
run produces the same people, resources and AI agents. All names and data are
fictional. Only the story resources (Arif, his agents, the Aurora repo) are
meant to be linked to the real GitHub demo organization later.

Run: python -m app.scripts.seed_company
"""
from __future__ import annotations

import random
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import AppRole, EmploymentStatus, ResourceState, ResourceType
from app.models import CompanyResource, Person
from app.scripts.seed_demo import ARIF_ID, PEOPLE as STORY_PEOPLE
from app.scripts.seed_demo import RESOURCES as ARIF_RESOURCES


RANDOM_SEED = 2026
ID_NAMESPACE = UUID("5b1c2d7e-8a43-4f0e-9c6b-2a1d3e4f5a60")

FARHANA_ID = UUID("11111111-1111-4111-8111-111111111111")
NABIL_ID = UUID("22222222-2222-4222-8222-222222222222")
TAHMID_ID = UUID("33333333-3333-4333-8333-333333333333")

CONFIDENTIAL_TRAINING = "SECURITY-CONFIDENTIAL"

# Fixed dates keep the output identical on every run. Time-limited agents
# expire after the final (26 Dec 2026); the expired one is already past.
FUTURE_EXPIRY = "2027-03-31T00:00:00+06:00"
PAST_EXPIRY = "2026-10-15T00:00:00+06:00"


FIRST_NAMES = [
    "Tanvir", "Nusrat", "Sabbir", "Farzana", "Mahmud", "Sadia", "Rakib", "Tasnim",
    "Imran", "Jannat", "Fahim", "Lamia", "Shakil", "Mehjabin", "Arman", "Rumana",
    "Zahid", "Anika", "Sohel", "Tahsin", "Rezaul", "Moumita", "Nayeem", "Sharmin",
    "Asif", "Rifat", "Shirin", "Kamrul", "Nabila", "Ehsan", "Puja", "Rashed",
    "Afsana", "Mizanur", "Tamanna", "Saiful", "Raisa", "Junaid", "Sumaiya", "Habib",
]

LAST_NAMES = [
    "Rahman", "Hossain", "Ahmed", "Islam", "Chowdhury", "Khan", "Uddin", "Akter",
    "Sarker", "Talukder", "Majumder", "Bhuiyan", "Karim", "Siddiqui", "Mollah", "Haque",
    "Das", "Roy", "Saha", "Begum",
]


# (department, head title, member titles, generated member count)
DEPARTMENTS = [
    ("ENGINEERING", "Engineering Manager",
     ["Software Engineer", "Senior Software Engineer", "DevOps Engineer",
      "QA Engineer", "Data Engineer"], 24),
    ("PRODUCT", "Head of Product", ["Product Manager", "Product Analyst"], 7),
    ("DESIGN", "Design Lead", ["Product Designer", "UX Researcher"], 5),
    ("SALES", "Head of Sales", ["Account Executive", "Sales Development Representative"], 11),
    ("SUPPORT", "Support Manager", ["Support Engineer", "Customer Success Associate"], 11),
    ("FINANCE", "Finance Manager", ["Accountant", "Financial Analyst"], 6),
    ("PEOPLE", None, ["HR Associate", "Talent Partner"], 5),
    ("IT_SECURITY", None, ["Security Engineer", "IT Administrator"], 4),
]

# Story characters already lead these departments.
STORY_HEADS = {"PEOPLE": FARHANA_ID, "IT_SECURITY": TAHMID_ID}

REPOSITORIES = ["aurora", "helios", "atlas", "billing-core", "support-portal"]
CONFIDENTIAL_REPOSITORIES = {"aurora"}


# (name, platform, purpose, system, resource, permission, risk tier, department)
AGENT_TEMPLATES = [
    ("Support Triage Bot", "n8n", "Routes new support tickets to the right queue",
     "zendesk", "support-queue", "write", "LOW", "SUPPORT"),
    ("Invoice Reconciler", "custom", "Matches bank payments to open invoices",
     "erp", "invoices", "write", "HIGH", "FINANCE"),
    ("Meeting Summarizer", "custom", "Summarizes recorded meetings into notes",
     "drive", "meeting-notes", "write", "LOW", "PRODUCT"),
    ("Helios Deploy Bot", "github_app", "Deploys Helios to staging after merges",
     "github", "helios", "write", "HIGH", "ENGINEERING"),
    ("Atlas Dependency Bot", "github_app", "Opens dependency update pull requests",
     "github", "atlas", "write", "LOW", "ENGINEERING"),
    ("Lead Enrichment Agent", "n8n", "Adds company data to new sales leads",
     "crm", "leads", "write", "LOW", "SALES"),
    ("Churn Risk Analyst", "custom", "Flags accounts with falling usage",
     "warehouse", "usage-metrics", "read", "LOW", "SUPPORT"),
    ("Expense Auditor", "n8n", "Checks expense claims against policy",
     "erp", "expenses", "read", "LOW", "FINANCE"),
    ("Release Notes Writer", "custom", "Drafts release notes from merged pull requests",
     "github", "helios", "read", "LOW", "PRODUCT"),
    ("Design Asset Tagger", "custom", "Tags new design files with components",
     "figma", "design-library", "write", "LOW", "DESIGN"),
    ("On-call Incident Bot", "n8n", "Opens incident channels and pages on-call",
     "pagerduty", "incidents", "write", "HIGH", "ENGINEERING"),
    ("Billing Migration Agent", "custom", "Migrates legacy billing records",
     "github", "billing-core", "write", "HIGH", "ENGINEERING"),
    ("Recruiting Scheduler", "n8n", "Books interview slots with candidates",
     "calendar", "interviews", "write", "LOW", "PEOPLE"),
    ("Access Review Assistant", "custom", "Prepares quarterly access review lists",
     "directory", "groups", "read", "LOW", "IT_SECURITY"),
    ("Contract Clause Checker", "custom", "Highlights non-standard contract clauses",
     "drive", "contracts", "read", "LOW", "SALES"),
    ("Knowledge Base Updater", "n8n", "Turns resolved tickets into help articles",
     "helpcenter", "articles", "write", "LOW", "SUPPORT"),
    ("Data Pipeline Monitor", "custom", "Restarts failed nightly data jobs",
     "warehouse", "pipelines", "write", "HIGH", "ENGINEERING"),
    ("Payroll Prep Assistant", "custom", "Collects payroll inputs for review",
     "hris", "payroll", "read", "HIGH", "FINANCE"),
    ("UX Feedback Clusterer", "custom", "Groups user feedback into themes",
     "drive", "research-notes", "read", "LOW", "DESIGN"),
    ("Support Portal Release Bot", "github_app", "Tags support portal releases",
     "github", "support-portal", "write", "HIGH", "ENGINEERING"),
    ("Quote Generator", "n8n", "Drafts sales quotes from price lists",
     "crm", "quotes", "write", "LOW", "SALES"),
    ("Phishing Report Triage", "custom", "Sorts reported phishing emails",
     "mail", "phishing-reports", "read", "LOW", "IT_SECURITY"),
]

# Agents that are already orphaned before the demo starts, so the map shows red
# on first load: (template index, reason).
PRESET_ORPHANS = {
    1: "SPONSOR_INACTIVE",
    5: "SPONSOR_DEPARTING",
    15: "EXPIRED",
}


def _id(kind: str, number: int) -> UUID:
    return uuid5(ID_NAMESPACE, f"{kind}:{number}")


def _slug(text: str) -> str:
    return "-".join(text.lower().replace("/", " ").split())


def _resource(
    person_id: UUID,
    resource_type: ResourceType,
    resource_key: str,
    status: ResourceState,
    details: dict,
) -> dict:
    return {
        "person_id": person_id,
        "resource_type": resource_type,
        "resource_key": resource_key,
        "status": status,
        "details_data": details,
        "idempotency_key": f"seed:company:{resource_key}",
    }


def _generate_people(rng: random.Random) -> list[dict]:
    used_emails = {person["email"] for person in STORY_PEOPLE}
    people: list[dict] = []
    number = 0

    def new_person(department: str, title: str, role: AppRole, manager_id) -> dict:
        nonlocal number
        number += 1
        while True:
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}@nexora.demo"
            if email not in used_emails:
                used_emails.add(email)
                break
        return {
            "id": _id("person", number),
            "name": f"{first} {last}",
            "email": email,
            "app_role": role,
            "employment_status": EmploymentStatus.ACTIVE,
            "department": department,
            "job_title": title,
            "manager_id": manager_id,
        }

    heads: list[dict] = []
    members: list[dict] = []
    for department, head_title, member_titles, count in DEPARTMENTS:
        head_id = STORY_HEADS.get(department)
        if head_id is None:
            head = new_person(department, head_title, AppRole.LINE_MANAGER, None)
            heads.append(head)
            head_id = head["id"]
        managers = [head_id]
        if department == "ENGINEERING":
            # Nabil leads one engineering team, the generated manager the other.
            managers = [NABIL_ID, head_id]
        for index in range(count):
            members.append(
                new_person(
                    department,
                    rng.choice(member_titles),
                    AppRole.EMPLOYEE,
                    managers[index % len(managers)],
                )
            )

    # A few leavers so the map is not all green.
    for person in rng.sample(members, 4):
        person["employment_status"] = EmploymentStatus.DEPARTING
    active = [p for p in members if p["employment_status"] == EmploymentStatus.ACTIVE]
    for person in rng.sample(active, 5):
        person["employment_status"] = EmploymentStatus.INACTIVE

    people.extend(heads)
    people.extend(members)
    return people


def _handle(person: dict) -> str:
    return person["email"].split("@")[0]


def _person_resources(rng: random.Random, person: dict, number: int) -> list[dict]:
    handle = _handle(person)
    gone = person["employment_status"] == EmploymentStatus.INACTIVE
    person_id = person["id"]
    resources = [
        _resource(
            person_id, ResourceType.EMAIL_ACCOUNT, f"email:{person['email']}",
            ResourceState.DISABLED if gone else ResourceState.ACTIVE,
            {"address": person["email"]},
        ),
        _resource(
            person_id, ResourceType.LAPTOP, f"LAPTOP-{number:03d}",
            ResourceState.RETURNED if gone else ResourceState.ASSIGNED,
            {"catalog_key": "LAPTOP-STD", "asset_tag": f"LAPTOP-{number:03d}"},
        ),
        _resource(
            person_id, ResourceType.TRAINING, f"training:SECURITY-BASE:{handle}",
            ResourceState.ACTIVE, {"catalog_key": "SECURITY-BASE"},
        ),
    ]
    if gone:
        return resources

    if person["department"] == "ENGINEERING":
        repo = rng.choice(REPOSITORIES)
        resources.append(
            _resource(
                person_id, ResourceType.GITHUB_ACCESS, f"github:{repo}:{handle}",
                ResourceState.ACTIVE,
                {"project": repo.upper(), "access_level": rng.choice(["READ", "WRITE"])},
            )
        )
        if repo in CONFIDENTIAL_REPOSITORIES:
            resources.append(
                _resource(
                    person_id, ResourceType.TRAINING,
                    f"training:{CONFIDENTIAL_TRAINING}:{handle}",
                    ResourceState.ACTIVE, {"catalog_key": CONFIDENTIAL_TRAINING},
                )
            )
    if rng.random() < 0.5:
        resources.append(
            _resource(
                person_id, ResourceType.WORK_ITEM, f"WORK-{number:03d}",
                ResourceState.OPEN,
                {"title": f"{person['department'].title()} task {number}"},
            )
        )
    if rng.random() < 0.3:
        resources.append(
            _resource(
                person_id, ResourceType.KNOWLEDGE_DOCUMENT, f"DOC-{number:03d}",
                ResourceState.ACTIVE,
                {"title": f"{person['department'].title()} handbook {number}"},
            )
        )
    return resources[:6]


def _story_resources() -> list[dict]:
    """Standard access for Farhana, Nabil and Tahmid; Nabil gets no
    confidential training, which the Policy V2 scene depends on."""
    resources: list[dict] = []
    for number, person in enumerate(STORY_PEOPLE, start=900):
        if person["id"] not in {FARHANA_ID, NABIL_ID, TAHMID_ID}:
            continue
        handle = _handle(person)
        resources.extend([
            _resource(
                person["id"], ResourceType.EMAIL_ACCOUNT, f"email:{person['email']}",
                ResourceState.ACTIVE, {"address": person["email"]},
            ),
            _resource(
                person["id"], ResourceType.LAPTOP, f"LAPTOP-{number:03d}",
                ResourceState.ASSIGNED,
                {"catalog_key": "LAPTOP-STD", "asset_tag": f"LAPTOP-{number:03d}"},
            ),
            _resource(
                person["id"], ResourceType.TRAINING, f"training:SECURITY-BASE:{handle}",
                ResourceState.ACTIVE, {"catalog_key": "SECURITY-BASE"},
            ),
        ])
    return resources


def _agents(rng: random.Random, people: list[dict]) -> list[dict]:
    by_status = {
        status: [p for p in people if p["employment_status"] == status]
        for status in EmploymentStatus
    }
    resources: list[dict] = []
    for index, template in enumerate(AGENT_TEMPLATES):
        name, platform, purpose, system, scope_resource, permission, risk, department = template
        reason = PRESET_ORPHANS.get(index)
        if reason == "SPONSOR_INACTIVE":
            pool = by_status[EmploymentStatus.INACTIVE]
        elif reason == "SPONSOR_DEPARTING":
            pool = by_status[EmploymentStatus.DEPARTING]
        else:
            pool = [
                p for p in by_status[EmploymentStatus.ACTIVE]
                if p["department"] == department
            ] or by_status[EmploymentStatus.ACTIVE]
        sponsor = rng.choice(pool)

        slug = _slug(name)
        agent_key = f"agent:{slug}"
        credential_key = f"credential:{slug}"
        if reason == "EXPIRED":
            expires_at = PAST_EXPIRY
        else:
            expires_at = FUTURE_EXPIRY if rng.random() < 0.35 else None

        resources.append(
            _resource(
                sponsor["id"], ResourceType.AI_AGENT, agent_key, ResourceState.ACTIVE,
                {
                    "agent_name": name,
                    "platform": platform,
                    "purpose": purpose,
                    "scopes": [
                        {"system": system, "resource": scope_resource, "permission": permission}
                    ],
                    "credential_key": credential_key,
                    "risk_tier": risk,
                    "expires_at": expires_at,
                    "last_active_at": f"2026-10-{rng.randint(1, 23):02d}T10:00:00+06:00",
                },
            )
        )
        resources.append(
            _resource(
                sponsor["id"], ResourceType.AGENT_CREDENTIAL, credential_key,
                ResourceState.ACTIVE,
                {
                    "agent_key": agent_key,
                    "kind": "api_token",
                    "system": system,
                    "permission": permission,
                },
            )
        )
    return resources


def build_company() -> tuple[list[dict], list[dict]]:
    """Return (people, resources) for the whole demo company, deterministically."""
    rng = random.Random(RANDOM_SEED)
    generated = _generate_people(rng)
    people = [*STORY_PEOPLE, *generated]

    resources = [
        {**values, "person_id": ARIF_ID} for values in ARIF_RESOURCES
    ]
    resources.extend(_story_resources())
    for number, person in enumerate(generated, start=1):
        resources.extend(_person_resources(rng, person, number))
    resources.extend(_agents(rng, generated))
    return people, resources


def all_person_ids() -> set[UUID]:
    people, _ = build_company()
    return {person["id"] for person in people}


def upsert_people(db: Session, people: list[dict]) -> None:
    # Managers first, so self-referencing manager_id rows exist before reports.
    ordered = sorted(people, key=lambda person: person["manager_id"] is not None)
    for values in ordered:
        person = db.get(Person, values["id"])
        if person is None:
            db.add(Person(**values))
        else:
            for field, value in values.items():
                if field != "id":
                    setattr(person, field, value)
        if values["manager_id"] is None:
            db.flush()
    db.flush()


def upsert_resources(db: Session, resources: list[dict]) -> None:
    for values in resources:
        resource = db.scalar(
            select(CompanyResource).where(
                CompanyResource.resource_key == values["resource_key"]
            )
        )
        if resource is None:
            db.add(CompanyResource(**values))
            continue
        resource.source_action_id = None
        for field, value in values.items():
            setattr(resource, field, value)
    db.flush()


def seed_company(db: Session) -> tuple[int, int]:
    people, resources = build_company()
    upsert_people(db, people)
    upsert_resources(db, resources)
    return len(people), len(resources)


def main() -> None:
    with SessionLocal() as db:
        try:
            people_count, resource_count = seed_company(db)
            db.commit()
        except Exception:
            db.rollback()
            raise

    print(
        f"Seeded Nexora Labs: {people_count} people and "
        f"{resource_count} resources (fictional demo data)."
    )


if __name__ == "__main__":
    main()
