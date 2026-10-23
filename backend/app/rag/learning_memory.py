from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, NAMESPACE_URL, uuid5

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import get_settings
from app.rag.embeddings import get_embedding_model
from app.rag.qdrant_client import get_qdrant_client


MEMORY_COLLECTION = "approved_operational_memory_v1"


@dataclass(frozen=True)
class MemorySearchResult:
    evidence_id: str
    learning_id: UUID
    trigger_type: str
    text: str
    score: float
    policy_version_ids: list[UUID]
    scope: dict


def _collection_name() -> str:
    settings = get_settings()
    return getattr(
        settings,
        "qdrant_memory_collection",
        MEMORY_COLLECTION,
    )


def ensure_memory_collection() -> str:
    settings = get_settings()
    collection_name = _collection_name()
    client = get_qdrant_client()

    try:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
        else:
            information = client.get_collection(collection_name)
            vectors = information.config.params.vectors
            existing_size = getattr(vectors, "size", None)
            if existing_size != settings.embedding_dimension:
                raise RuntimeError(
                    f"Memory collection dimension is {existing_size}, "
                    f"but {settings.embedding_dimension} is required."
                )

        for field_name in (
            "status",
            "source_type",
            "trigger_type",
            "case_types",
            "departments",
            "roles",
            "sensitivity",
        ):
            information = client.get_collection(collection_name)
            if field_name not in information.payload_schema:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=PayloadSchemaType.KEYWORD,
                    wait=True,
                )

        return collection_name
    finally:
        client.close()


def build_learning_identity(
    learning_id: UUID,
    content_hash: str,
) -> tuple[str, UUID]:
    evidence_id = f"MEM-{learning_id}-C0"
    point_id = uuid5(
        NAMESPACE_URL,
        f"{evidence_id}:{content_hash}",
    )
    return evidence_id, point_id


def upsert_learning_memory(
    *,
    learning_id: UUID,
    trigger_type: str,
    memory_text: str,
    content_hash: str,
    scope: dict,
    policy_version_ids: list[UUID],
) -> tuple[str, UUID]:
    settings = get_settings()
    collection_name = ensure_memory_collection()
    evidence_id, point_id = build_learning_identity(
        learning_id,
        content_hash,
    )

    vector = get_embedding_model().embed_query(memory_text)
    if len(vector) != settings.embedding_dimension:
        raise RuntimeError(
            f"Expected {settings.embedding_dimension} embedding dimensions, "
            f"received {len(vector)}."
        )

    payload = {
        "source_type": "LEARNING",
        "learning_id": str(learning_id),
        "status": "APPROVED",
        "trigger_type": trigger_type,
        "case_types": list(scope.get("case_types") or []),
        "departments": list(scope.get("departments") or []),
        "roles": list(scope.get("roles") or []),
        "sensitivity": str(scope.get("sensitivity") or "INTERNAL"),
        "policy_version_ids": [str(item) for item in policy_version_ids],
        "evidence_id": evidence_id,
        "content_hash": content_hash,
        "text": memory_text,
    }

    client = get_qdrant_client()
    try:
        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=payload,
                )
            ],
            wait=True,
        )
    finally:
        client.close()

    return evidence_id, point_id


def search_learning_memory(
    *,
    query: str,
    case_type: str,
    department: str,
    role: str | None = None,
    sensitivity: str | None = None,
    top_k: int = 2,
) -> list[MemorySearchResult]:
    collection_name = ensure_memory_collection()
    vector = get_embedding_model().embed_query(query)

    must = [
        FieldCondition(key="status", match=MatchValue(value="APPROVED")),
        FieldCondition(key="case_types", match=MatchValue(value=case_type)),
        FieldCondition(key="departments", match=MatchValue(value=department)),
    ]
    if role:
        must.append(
            FieldCondition(key="roles", match=MatchValue(value=role))
        )
    if sensitivity:
        must.append(
            FieldCondition(
                key="sensitivity",
                match=MatchValue(value=sensitivity),
            )
        )

    query_filter = Filter(must=must)
    client = get_qdrant_client()
    try:
        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=collection_name,
                query=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
            points = response.points
        else:
            points = client.search(
                collection_name=collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
    finally:
        client.close()

    results: list[MemorySearchResult] = []
    for point in points:
        payload = dict(point.payload or {})
        learning_id = payload.get("learning_id")
        if not learning_id:
            continue
        results.append(
            MemorySearchResult(
                evidence_id=str(payload.get("evidence_id") or ""),
                learning_id=UUID(str(learning_id)),
                trigger_type=str(payload.get("trigger_type") or "HANDOVER"),
                text=str(payload.get("text") or ""),
                score=float(point.score or 0.0),
                policy_version_ids=[
                    UUID(str(item))
                    for item in payload.get("policy_version_ids") or []
                ],
                scope={
                    "case_types": payload.get("case_types") or [],
                    "departments": payload.get("departments") or [],
                    "roles": payload.get("roles") or [],
                    "sensitivity": payload.get("sensitivity"),
                },
            )
        )

    return results
