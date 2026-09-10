from sqlalchemy.orm import Session

from app.rag.bm25_retriever import (
    search_current_policies_bm25,
)
from app.rag.policy_retriever import (
    PolicySearchResult,
    search_current_policies,
)


def reciprocal_rank_fusion(
    rankings: list[list[PolicySearchResult]],
    *,
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[PolicySearchResult]:
    fused_scores: dict[str, float] = {}
    documents: dict[str, PolicySearchResult] = {}

    for ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            evidence_id = result.evidence_id

            fused_scores[evidence_id] = (
                fused_scores.get(evidence_id, 0.0)
                + 1.0 / (rrf_k + rank)
            )

            documents[evidence_id] = result

    ranked_evidence_ids = sorted(
        fused_scores,
        key=lambda evidence_id: (
            -fused_scores[evidence_id],
            evidence_id,
        ),
    )

    results = []

    for evidence_id in ranked_evidence_ids[:top_k]:
        document = documents[evidence_id]

        results.append(
            PolicySearchResult(
                evidence_id=document.evidence_id,
                policy_code=document.policy_code,
                version_number=document.version_number,
                text=document.text,
                score=fused_scores[evidence_id],
            )
        )

    return results


def search_current_policies_hybrid(
    db: Session,
    query: str,
    top_k: int = 5,
    candidate_k: int = 10,
) -> list[PolicySearchResult]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    candidate_k = max(candidate_k, top_k)

    dense_results = search_current_policies(
        db,
        query=query,
        top_k=candidate_k,
    )

    bm25_results = search_current_policies_bm25(
        db,
        query=query,
        top_k=candidate_k,
    )

    return reciprocal_rank_fusion(
        [dense_results, bm25_results],
        top_k=top_k,
    )