from dataclasses import dataclass

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.enums import PolicyState
from app.models import PolicyVersion
from app.rag.embeddings import get_embedding_model
from app.rag.qdrant_client import get_qdrant_client


@dataclass
class PolicySearchResult:
    evidence_id: str
    policy_code: str
    version_number: int
    text: str
    score: float


def search_current_policies(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[PolicySearchResult]:
    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    settings = get_settings()

    current_policy_ids = list(
        db.scalars(
            select(PolicyVersion.id).where(
                PolicyVersion.status == PolicyState.CURRENT
            )
        )
    )

    if not current_policy_ids:
        return []

    query_vector = get_embedding_model().embed_query(query)

    current_policy_filter = Filter(
        must=[
            FieldCondition(
                key="policy_version_id",
                match=MatchAny(
                    any=[
                        str(policy_id)
                        for policy_id in current_policy_ids
                    ]
                ),
            )
        ]
    )

    client = get_qdrant_client()

    try:
        response = client.query_points(
            collection_name=settings.qdrant_policy_collection,
            query=query_vector,
            query_filter=current_policy_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
    finally:
        client.close()

    results = []

    for point in response.points:
        payload = point.payload or {}

        results.append(
            PolicySearchResult(
                evidence_id=str(payload["evidence_id"]),
                policy_code=str(payload["policy_code"]),
                version_number=int(payload["version_number"]),
                text=str(payload["text"]),
                score=float(point.score),
            )
        )

    return results