from fastapi import FastAPI, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.agents.routes import router as agents_router
from app.approvals.routes import router as approvals_router
from app.audit.routes import router as audit_router
from app.cases.routes import router as cases_router
from app.config import get_settings
from app.database import check_database_connection
from app.execution.routes import router as execution_router
from app.handover.routes import router as handover_router
from app.learning.routes import router as learning_router
from app.offboarding.routes import router as offboarding_router
from app.planning.routes import router as planning_router
from app.policy_guardian.routes import router as policy_guardian_router
from app.rag.qdrant_client import check_qdrant_connection
from app.revisions.routes import router as revisions_router
from app.routes.mock_company import router as mock_company_router
from app.security.routes import router as security_router


settings = get_settings()

OPENAPI_TAGS = [
    {
        "name": "cases",
        "description": "Case intake, case state, and policy-context operations.",
    },
    {
        "name": "planning",
        "description": "Policy-grounded AI planning for operational cases.",
    },
    {
        "name": "approvals",
        "description": "Human-in-the-loop approval and decision endpoints.",
    },
    {
        "name": "execution",
        "description": "Approved action dispatch, retry, and verification.",
    },
    {
        "name": "offboarding",
        "description": "Resource-aware employee offboarding planning.",
    },
    {
        "name": "handover",
        "description": "Targeted handover capture and review.",
    },
    {
        "name": "learning",
        "description": "Approved operational learning and reusable memory.",
    },
    {
        "name": "revisions",
        "description": "Manager corrections and plan revision workflows.",
    },
    {
        "name": "policy-guardian",
        "description": (
            "Policy-version change analysis, impact detection, and "
            "controlled remediation."
        ),
    },
    {
        "name": "audit",
        "description": "Case timeline and audit-coverage inspection.",
    },
    {
        "name": "security",
        "description": (
            "Access-event anomaly scoring and human-reviewed security alerts."
        ),
    },
    {
        "name": "mock-company",
        "description": "Development/demo company-resource execution adapter.",
    },
]

app = FastAPI(
    title="LivingOps AI",
    version="0.2.0-stage2",
    description=(
        "AI operations command center for policy-grounded case planning, "
        "human approval, execution, auditability, approved learning, "
        "policy-change governance, and anomaly detection."
    ),
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(cases_router)
app.include_router(planning_router)
app.include_router(approvals_router)
app.include_router(execution_router)
app.include_router(offboarding_router)
app.include_router(handover_router)
app.include_router(learning_router)
app.include_router(revisions_router)
app.include_router(audit_router)
app.include_router(security_router)
app.include_router(mock_company_router)
app.include_router(policy_guardian_router)
app.include_router(agents_router)


@app.get(
    "/",
    tags=["system"],
    summary="LivingOps API root",
)
def root() -> dict[str, str]:
    return {
        "message": "Welcome to LivingOps AI!",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    tags=["system"],
    summary="Check backend dependencies",
    response_description="Application, PostgreSQL, and Qdrant health.",
)
def health(response: Response) -> dict[str, str]:
    database_status = "ok"
    qdrant_status = "ok"

    try:
        check_database_connection()
    except SQLAlchemyError:
        database_status = "failed"

    try:
        check_qdrant_connection()
    except Exception:
        qdrant_status = "failed"

    overall_status = (
        "ok"
        if database_status == "ok" and qdrant_status == "ok"
        else "degraded"
    )

    if overall_status == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "application": settings.app_name,
        "environment": settings.app_env,
        "database": database_status,
        "qdrant": qdrant_status,
    }
