from qdrant_client import QdrantClient

from app.config import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )


def check_qdrant_connection() -> list[str]:
    client = get_qdrant_client()

    try:
        response = client.get_collections()
        return [collection.name for collection in response.collections]
    finally:
        client.close()