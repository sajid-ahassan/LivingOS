from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.contracts import BaseGraphState


StateUpdate = dict[str, Any]

LoadCaseFn = Callable[[str], dict[str, Any]]
InventoryResourcesFn = Callable[[dict[str, Any]], list[dict[str, Any]]]
RetrieveContextFn = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]
GeneratePlanFn = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any]],
    dict[str, Any],
]
ValidatePlanFn = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any]],
    list[str],
]
GenerateQuestionsFn = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]],
    list[str],
]
ValidateQuestionsFn = Callable[
    [list[str], dict[str, Any], list[dict[str, Any]]],
    list[str],
]
RepairFn = Callable[
    [dict[str, Any], list[str], dict[str, Any]],
    dict[str, Any],
]


class OffboardingGraphState(BaseGraphState, total=False):
    questions: list[str]
    question_errors: list[str]
    repair_boundary: str


def build_offboarding_graph(
    *,
    load_case_fn: LoadCaseFn,
    inventory_resources_fn: InventoryResourcesFn,
    retrieve_context_fn: RetrieveContextFn,
    generate_plan_fn: GeneratePlanFn,
    validate_plan_fn: ValidatePlanFn,
    generate_questions_fn: GenerateQuestionsFn,
    validate_questions_fn: ValidateQuestionsFn,
    repair_plan_fn: RepairFn,
    repair_questions_fn: RepairFn,
):
    """
    Bounded synchronous offboarding workflow.

    One total repair is allowed across both validation boundaries:
    either plan validation or question validation.
    """

    def load_case(state: OffboardingGraphState) -> StateUpdate:
        case_id = state.get("case_id")
        if not case_id:
            raise ValueError("case_id is required")

        facts = load_case_fn(case_id)
        return {
            "case_facts": facts,
            "repair_count": int(state.get("repair_count", 0)),
        }

    def inventory_resources(state: OffboardingGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        resources = inventory_resources_fn(facts)
        return {"resources": resources}

    def retrieve_context(state: OffboardingGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        resources = state.get("resources") or []
        retrieval = retrieve_context_fn(facts, resources)
        return {"retrieval": retrieval}

    def generate_plan(state: OffboardingGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        resources = state.get("resources") or []
        retrieval = state.get("retrieval") or {}

        draft = generate_plan_fn(
            facts,
            resources,
            retrieval,
        )
        return {"draft": draft}

    def validate_plan(state: OffboardingGraphState) -> StateUpdate:
        draft = state.get("draft") or {}
        resources = state.get("resources") or []
        retrieval = state.get("retrieval") or {}

        errors = validate_plan_fn(
            draft,
            resources,
            retrieval,
        )
        return {
            "validation_errors": list(errors),
            "repair_boundary": "plan",
        }

    def repair_plan(state: OffboardingGraphState) -> StateUpdate:
        draft = state.get("draft") or {}
        errors = state.get("validation_errors") or []
        retrieval = state.get("retrieval") or {}

        repaired = repair_plan_fn(
            draft,
            errors,
            retrieval,
        )
        return {
            "draft": repaired,
            "repair_count": int(state.get("repair_count", 0)) + 1,
            "validation_errors": [],
        }

    def generate_questions(state: OffboardingGraphState) -> StateUpdate:
        facts = state.get("case_facts") or {}
        resources = state.get("resources") or []
        retrieval = state.get("retrieval") or {}
        draft = state.get("draft") or {}

        questions = generate_questions_fn(
            facts,
            resources,
            retrieval,
            draft,
        )
        return {"questions": questions}

    def validate_questions(state: OffboardingGraphState) -> StateUpdate:
        questions = state.get("questions") or []
        facts = state.get("case_facts") or {}
        resources = state.get("resources") or []

        errors = validate_questions_fn(
            questions,
            facts,
            resources,
        )

        if not errors:
            final_output = dict(state.get("draft") or {})
            final_output["targeted_questions"] = questions
            return {
                "question_errors": [],
                "final_output": final_output,
                "terminal_state": "VALID",
            }

        return {
            "question_errors": list(errors),
            "repair_boundary": "questions",
        }

    def repair_questions(state: OffboardingGraphState) -> StateUpdate:
        current = {
            "questions": state.get("questions") or [],
        }
        errors = state.get("question_errors") or []
        retrieval = state.get("retrieval") or {}

        repaired = repair_questions_fn(
            current,
            errors,
            retrieval,
        )

        questions = repaired.get("questions", [])
        return {
            "questions": questions,
            "repair_count": int(state.get("repair_count", 0)) + 1,
            "question_errors": [],
        }

    def finish_review(state: OffboardingGraphState) -> StateUpdate:
        final_output = dict(state.get("draft") or {})
        if state.get("questions"):
            final_output["targeted_questions"] = state["questions"]

        return {
            "final_output": final_output,
            "terminal_state": "NEEDS_HUMAN_REVIEW",
        }

    def route_after_plan_validation(state: OffboardingGraphState) -> str:
        if not state.get("validation_errors"):
            return "questions"

        if int(state.get("repair_count", 0)) == 0:
            return "repair_plan"

        return "review"

    def route_after_question_validation(state: OffboardingGraphState) -> str:
        if not state.get("question_errors"):
            return "end"

        if int(state.get("repair_count", 0)) == 0:
            return "repair_questions"

        return "review"

    graph = StateGraph(OffboardingGraphState)

    graph.add_node("load_case", load_case)
    graph.add_node("inventory_resources", inventory_resources)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("validate_plan", validate_plan)
    graph.add_node("repair_plan", repair_plan)
    graph.add_node("generate_questions", generate_questions)
    graph.add_node("validate_questions", validate_questions)
    graph.add_node("repair_questions", repair_questions)
    graph.add_node("finish_review", finish_review)

    graph.add_edge(START, "load_case")
    graph.add_edge("load_case", "inventory_resources")
    graph.add_edge("inventory_resources", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")

    graph.add_conditional_edges(
        "validate_plan",
        route_after_plan_validation,
        {
            "questions": "generate_questions",
            "repair_plan": "repair_plan",
            "review": "finish_review",
        },
    )

    graph.add_edge("repair_plan", "validate_plan")
    graph.add_edge("generate_questions", "validate_questions")

    graph.add_conditional_edges(
        "validate_questions",
        route_after_question_validation,
        {
            "end": END,
            "repair_questions": "repair_questions",
            "review": "finish_review",
        },
    )

    graph.add_edge("repair_questions", "validate_questions")
    graph.add_edge("finish_review", END)

    return graph.compile()
