from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.contracts import BaseGraphState


StateUpdate = dict[str, Any]
LoadCaseFn = Callable[[str], dict[str, Any]]
RetrieveContextFn = Callable[[dict[str, Any]], dict[str, Any]]
GeneratePlanFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
ValidatePlanFn = Callable[
    [dict[str, Any], dict[str, Any]],
    list[str],
]
RepairPlanFn = Callable[
    [dict[str, Any], list[str], dict[str, Any]],
    dict[str, Any],
]


def build_onboarding_graph(
    *,
    load_case_fn: LoadCaseFn,
    retrieve_context_fn: RetrieveContextFn,
    generate_plan_fn: GeneratePlanFn,
    validate_plan_fn: ValidatePlanFn,
    repair_plan_fn: RepairPlanFn,
):
    """
    Build the bounded synchronous onboarding planning graph.

    Business persistence stays outside the graph. Injected functions may read
    through existing services, but graph nodes themselves only return state
    updates.
    """

    def load_case(state: BaseGraphState) -> StateUpdate:
        case_id = state.get("case_id")
        if not case_id:
            raise ValueError("case_id is required")

        facts = load_case_fn(case_id)
        return {
            "case_facts": facts,
            "repair_count": int(state.get("repair_count", 0)),
        }

    def retrieve_context(state: BaseGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        retrieval = retrieve_context_fn(facts)
        return {"retrieval": retrieval}

    def generate_plan(state: BaseGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        retrieval = state.get("retrieval") or {}
        draft = generate_plan_fn(facts, retrieval)
        return {"draft": draft}

    def validate_plan(state: BaseGraphState) -> StateUpdate:
        draft = state.get("draft") or {}
        retrieval = state.get("retrieval") or {}

        errors = validate_plan_fn(draft, retrieval)

        if errors:
            return {
                "validation_errors": list(errors),
                "terminal_state": "INVALID",
            }

        return {
            "validation_errors": [],
            "final_output": draft,
            "terminal_state": "VALID",
        }

    def repair_plan(state: BaseGraphState) -> StateUpdate:
        draft = state.get("draft") or {}
        errors = state.get("validation_errors") or []
        retrieval = state.get("retrieval") or {}

        repaired = repair_plan_fn(draft, errors, retrieval)

        return {
            "draft": repaired,
            "repair_count": int(state.get("repair_count", 0)) + 1,
            "validation_errors": [],
        }

    def finish_review(state: BaseGraphState) -> StateUpdate:
        return {
            "final_output": state.get("draft") or {},
            "terminal_state": "NEEDS_HUMAN_REVIEW",
        }

    def route_after_validation(state: BaseGraphState) -> str:
        if not state.get("validation_errors"):
            return "end"

        if int(state.get("repair_count", 0)) == 0:
            return "repair"

        return "review"

    graph = StateGraph(BaseGraphState)

    graph.add_node("load_case", load_case)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("validate_plan", validate_plan)
    graph.add_node("repair_plan", repair_plan)
    graph.add_node("finish_review", finish_review)

    graph.add_edge(START, "load_case")
    graph.add_edge("load_case", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")

    graph.add_conditional_edges(
        "validate_plan",
        route_after_validation,
        {
            "end": END,
            "repair": "repair_plan",
            "review": "finish_review",
        },
    )

    graph.add_edge("repair_plan", "validate_plan")
    graph.add_edge("finish_review", END)

    return graph.compile()
