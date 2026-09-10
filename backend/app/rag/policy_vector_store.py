from uuid import UUID

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)

from app.config import get_settings
from app.rag.embeddings import get_embedding_model
from app.rag.policy_chunks import PolicyChunk
from app.rag.qdrant_client import get_qdrant_client


def store_policy_chunks(chunks: list[PolicyChunk]) -> int:
    if not chunks:
        raise ValueError("No policy chunks were provided.")

    settings = get_settings()
    embedding_model = get_embedding_model()

    texts = [chunk.text for chunk in chunks]
    vectors = embedding_model.embed_documents(texts)

    if len(vectors) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match chunk count."
        )

    points = []

    for chunk, vector in zip(chunks, vectors, strict=True):
        if len(vector) != settings.embedding_dimension:
            raise RuntimeError(
                f"Expected {settings.embedding_dimension} dimensions, "
                f"received {len(vector)}."
            )

        points.append(
            PointStruct(
                id=chunk.point_id,
                vector=vector,
                payload=chunk.payload,
            )
        )

    client = get_qdrant_client()

    try:
        client.upsert(
            collection_name=settings.qdrant_policy_collection,
            points=points,
            wait=True,
        )
    finally:
        client.close()

    return len(points)


def count_policy_chunks(policy_version_id: UUID) -> int:
    settings = get_settings()
    client = get_qdrant_client()

    policy_filter = Filter(
        must=[
            FieldCondition(
                key="policy_version_id",
                match=MatchValue(
                    value=str(policy_version_id)
                ),
            )
        ]
    )

    try:
        result = client.count(
            collection_name=settings.qdrant_policy_collection,
            count_filter=policy_filter,
            exact=True,
        )

        return result.count
    finally:
        client.close()