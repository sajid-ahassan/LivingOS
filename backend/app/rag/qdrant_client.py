from qdrant_client import QdrantClient

from app.config import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )


def check_qdrant_connection() -> None:
    settings = get_settings()
    client = get_qdrant_client()

    try:
        client.get_collection(
            collection_name=settings.qdrant_policy_collection
        )
    finally:
        client.close()