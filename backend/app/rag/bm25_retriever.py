import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import PolicyState
from app.models import PolicyVersion
from app.rag.policy_loader import split_policy_text
from app.rag.policy_retriever import PolicySearchResult


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search_current_policies_bm25(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[PolicySearchResult]:
    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    current_policies = list(
        db.scalars(
            select(PolicyVersion).where(
                PolicyVersion.status == PolicyState.CURRENT
            )
        )
    )

    documents = []

    for policy in current_policies:
        chunks = split_policy_text(policy.content_text)

        for index, chunk in enumerate(chunks):
            documents.append(
                PolicySearchResult(
                    evidence_id=(
                        f"POL-{policy.policy_code}"
                        f"-V{policy.version_number}-C{index}"
                    ),
                    policy_code=policy.policy_code,
                    version_number=policy.version_number,
                    text=chunk,
                    score=0.0,
                )
            )

    if not documents:
        return []

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    tokenized_corpus = [
        tokenize(document.text)
        for document in documents
    ]

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(documents)),
        key=lambda index: float(scores[index]),
        reverse=True,
    )

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        if score <= 0:
            continue

        document = documents[index]

        results.append(
            PolicySearchResult(
                evidence_id=document.evidence_id,
                policy_code=document.policy_code,
                version_number=document.version_number,
                text=document.text,
                score=score,
            )
        )

        if len(results) == top_k:
            break

    return results