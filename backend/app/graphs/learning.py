from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.contracts import BaseGraphState


StateUpdate = dict[str, Any]

LoadCompletedCaseFn = Callable[[str], dict[str, Any]]
CompareRevisionsFn = Callable[[dict[str, Any]], dict[str, Any]]
RetrieveCurrentPolicyFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
DraftCandidateFn = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]],
    dict[str, Any],
]
SanitizeFn = Callable[[dict[str, Any]], dict[str, Any]]
ValidateScopeFn = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]],
    list[str],
]


class LearningGraphState(BaseGraphState, total=False):
    comparison: dict[str, Any]
    policy_context: dict[str, Any]
    candidate: dict[str, Any]


def build_learning_graph(
    *,
    load_completed_case_fn: LoadCompletedCaseFn,
    compare_revisions_fn: CompareRevisionsFn,
    retrieve_current_policy_fn: RetrieveCurrentPolicyFn,
    draft_candidate_fn: DraftCandidateFn,
    sanitize_fn: SanitizeFn,
    validate_scope_fn: ValidateScopeFn,
):
    """
    Bounded synchronous learning workflow.

    The graph creates only a candidate. Approval/indexing remain outside
    LangGraph and are handled by FastAPI/PostgreSQL services.
    """

    def load_completed_case(state: LearningGraphState) -> StateUpdate:
        case_id = state.get("case_id")
        if not case_id:
            raise ValueError("case_id is required")

        facts = load_completed_case_fn(case_id)
        return {"case_facts": facts}

    def compare_revisions(state: LearningGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        comparison = compare_revisions_fn(facts)
        return {"comparison": comparison}

    def retrieve_current_policy(state: LearningGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        comparison = state.get("comparison") or {}

        policy_context = retrieve_current_policy_fn(
            facts,
            comparison,
        )
        return {"policy_context": policy_context}

    def draft_candidate(state: LearningGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        comparison = state.get("comparison") or {}
        policy_context = state.get("policy_context") or {}

        candidate = draft_candidate_fn(
            facts,
            comparison,
            policy_context,
        )
        return {"candidate": candidate}

    def sanitize(state: LearningGraphState) -> StateUpdate:
        candidate = state.get("candidate") or {}
        sanitized = sanitize_fn(candidate)
        return {"candidate": sanitized}

    def validate_scope(state: LearningGraphState) -> StateUpdate:
        candidate = state.get("candidate") or {}
        facts = state.get("case_facts") or {}
        policy_context = state.get("policy_context") or {}

        errors = validate_scope_fn(
            candidate,
            facts,
            policy_context,
        )

        if errors:
            return {
                "validation_errors": list(errors),
                "final_output": candidate,
                "terminal_state": "NEEDS_HUMAN_REVIEW",
            }

        return {
            "validation_errors": [],
            "final_output": candidate,
            "terminal_state": "VALID",
        }

    def route_after_validation(state: LearningGraphState) -> str:
        if state.get("validation_errors"):
            return "review"
        return "end"

    graph = StateGraph(LearningGraphState)

    graph.add_node("load_completed_case", load_completed_case)
    graph.add_node("compare_revisions", compare_revisions)
    graph.add_node("retrieve_current_policy", retrieve_current_policy)
    graph.add_node("draft_candidate", draft_candidate)
    graph.add_node("sanitize", sanitize)
    graph.add_node("validate_scope", validate_scope)

    graph.add_edge(START, "load_completed_case")
    graph.add_edge("load_completed_case", "compare_revisions")
    graph.add_edge("compare_revisions", "retrieve_current_policy")
    graph.add_edge("retrieve_current_policy", "draft_candidate")
    graph.add_edge("draft_candidate", "sanitize")
    graph.add_edge("sanitize", "validate_scope")

    graph.add_conditional_edges(
        "validate_scope",
        route_after_validation,
        {
            "review": END,
            "end": END,
        },
    )

    return graph.compile()
