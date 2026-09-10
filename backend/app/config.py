from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    
    n8n_provisioning_webhook: str
    n8n_shared_token: str
    n8n_callback_base_url: str = "http://127.0.0.1:8000"
    request_timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()