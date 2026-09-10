from fastapi import FastAPI, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import check_database_connection


settings = get_settings()

from app.routes.mock_company import (
    router as mock_company_router,
)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

from app.database import get_db

app.include_router(mock_company_router)



@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Welcome to LivingOps AI!"}




@app.get("/health")
def health(response: Response) -> dict[str, str]:
    try:
        check_database_connection()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "degraded",
            "application": settings.app_name,
            "environment": settings.app_env,
            "database": "failed",
        }

    return {
        "status": "ok",
        "application": settings.app_name,
        "environment": settings.app_env,
        "database": "ok",
    }