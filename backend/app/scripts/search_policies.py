from app.database import SessionLocal
from app.rag.bm25_retriever import (
    search_current_policies_bm25,
)
from app.rag.hybrid_retriever import (
    reciprocal_rank_fusion,
)
from app.rag.policy_retriever import (
    search_current_policies,
)


TEST_CASES = [
    {
        "query": "Who must approve confidential project access?",
        "expected": "ACCESS",
    },
    {
        "query": "How must a company laptop be assigned and recorded?",
        "expected": "EQUIPMENT",
    },
    {
        "query": (
            "Who must approve the handover before reusable "
            "knowledge is stored?"
        ),
        "expected": "OFFBOARDING",
    },
]


def get_top_policy(results: list) -> str:
    if not results:
        return "NONE"

    return results[0].policy_code


def main() -> None:
    dense_passed = 0
    bm25_passed = 0
    hybrid_passed = 0

    with SessionLocal() as db:
        for test_case in TEST_CASES:
            query = test_case["query"]
            expected = test_case["expected"]

            dense_results = search_current_policies(
                db,
                query=query,
                top_k=3,
            )

            bm25_results = search_current_policies_bm25(
                db,
                query=query,
                top_k=3,
            )

            hybrid_results = reciprocal_rank_fusion(
                [dense_results, bm25_results],
                top_k=3,
            )

            dense_top = get_top_policy(dense_results)
            bm25_top = get_top_policy(bm25_results)
            hybrid_top = get_top_policy(hybrid_results)

            if dense_top == expected:
                dense_passed += 1

            if bm25_top == expected:
                bm25_passed += 1

            if hybrid_top == expected:
                hybrid_passed += 1

            print()
            print("Question:", query)
            print("Expected:", expected)

            print()
            print("Dense top result:", dense_top)

            if dense_results:
                print(
                    "Dense evidence:",
                    dense_results[0].evidence_id,
                )
                print(
                    "Dense score:",
                    round(dense_results[0].score, 4),
                )

            print()
            print("BM25 top result:", bm25_top)

            if bm25_results:
                print(
                    "BM25 evidence:",
                    bm25_results[0].evidence_id,
                )
                print(
                    "BM25 score:",
                    round(bm25_results[0].score, 4),
                )

            print()
            print("Hybrid top result:", hybrid_top)

            if hybrid_results:
                print(
                    "Hybrid evidence:",
                    hybrid_results[0].evidence_id,
                )
                print(
                    "Hybrid RRF score:",
                    round(hybrid_results[0].score, 6),
                )

            print("-" * 60)

    total = len(TEST_CASES)

    print()
    print("Retrieval summary")
    print("Dense top-1:", f"{dense_passed}/{total}")
    print("BM25 top-1:", f"{bm25_passed}/{total}")
    print("Hybrid top-1:", f"{hybrid_passed}/{total}")


if __name__ == "__main__":
    main()