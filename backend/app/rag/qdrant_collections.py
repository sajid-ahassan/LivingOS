from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    VectorParams,
)

from app.config import get_settings
from app.rag.qdrant_client import get_qdrant_client


def ensure_policy_collection() -> str:
    settings = get_settings()
    client = get_qdrant_client()
    collection_name = settings.qdrant_policy_collection

    try:
        if client.collection_exists(collection_name):
            information = client.get_collection(collection_name)
            vectors = information.config.params.vectors
            existing_size = getattr(vectors, "size", None)

            if existing_size != settings.embedding_dimension:
                raise RuntimeError(
                    f"Existing collection dimension is {existing_size}, "
                    f"but {settings.embedding_dimension} is required."
                )

            return f"Collection already exists: {collection_name}"

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )

        return f"Collection created: {collection_name}"
    finally:
        client.close()
        
        
        
def ensure_policy_version_index() -> str:
    settings = get_settings()
    client = get_qdrant_client()
    field_name = "policy_version_id"

    try:
        information = client.get_collection(
            settings.qdrant_policy_collection
        )

        if field_name in information.payload_schema:
            return f"Payload index already exists: {field_name}"

        client.create_payload_index(
            collection_name=settings.qdrant_policy_collection,
            field_name=field_name,
            field_schema=PayloadSchemaType.UUID,
            wait=True,
        )

        return f"Payload index created: {field_name}"
    finally:
        client.close()