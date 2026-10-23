from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    app_name: str = "LivingOps AI"
    app_env: str = "development"
    database_url: str

    qdrant_url: str
    qdrant_api_key: str
    qdrant_policy_collection: str = "policy_knowledge_v1"

    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    openai_chat_model: str = "gpt-4o-mini"

    n8n_provisioning_webhook: str
    n8n_shared_token: str
    request_timeout_seconds: int = 30

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg3_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        return value

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            BACKEND_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
