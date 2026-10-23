from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.contracts import BaseGraphState


StateUpdate = dict[str, Any]

LoadExactVersionsFn = Callable[[str, str], dict[str, Any]]
DeterministicDiffFn = Callable[[dict[str, Any]], dict[str, Any]]
ExplainChangesFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
LoadPolicyLinksFn = Callable[[dict[str, Any]], list[dict[str, Any]]]
ClassifyImpactsFn = Callable[
    [dict[str, Any], list[dict[str, Any]]],
    list[dict[str, Any]],
]
ValidateImpactsFn = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any]],
    list[str],
]
PersistResultFn = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any]],
    dict[str, Any],
]


class GuardianGraphState(BaseGraphState, total=False):
    old_version_id: str
    new_version_id: str
    versions: dict[str, Any]
    diff: dict[str, Any]
    change_analysis: dict[str, Any]
    policy_links: list[dict[str, Any]]
    impacts: list[dict[str, Any]]
    persisted_result: dict[str, Any]


def build_guardian_graph(
    *,
    load_exact_versions_fn: LoadExactVersionsFn,
    deterministic_diff_fn: DeterministicDiffFn,
    explain_changes_fn: ExplainChangesFn,
    load_policy_links_fn: LoadPolicyLinksFn,
    classify_impacts_fn: ClassifyImpactsFn,
    validate_impacts_fn: ValidateImpactsFn,
    persist_result_fn: PersistResultFn,
):
    """
    Build the bounded synchronous Policy Guardian graph.

    The graph compares only the exact supplied old/new policy versions.
    Affected targets come only from policy links. The LLM may explain changes
    and impacts, but it cannot invent version IDs or affected target IDs.
    """

    def load_exact_versions(
        state: GuardianGraphState,
    ) -> StateUpdate:
        old_version_id = state.get("old_version_id")
        new_version_id = state.get("new_version_id")

        if not old_version_id or not new_version_id:
            raise ValueError(
                "old_version_id and new_version_id are required"
            )

        versions = load_exact_versions_fn(
            old_version_id,
            new_version_id,
        )

        return {"versions": versions}

    def deterministic_diff(
        state: GuardianGraphState,
    ) -> StateUpdate:
        versions = state.get("versions") or {}
        diff = deterministic_diff_fn(versions)
        return {"diff": diff}

    def explain_changes(
        state: GuardianGraphState,
    ) -> StateUpdate:
        versions = state.get("versions") or {}
        diff = state.get("diff") or {}

        analysis = explain_changes_fn(
            versions,
            diff,
        )

        return {"change_analysis": analysis}

    def load_policy_links(
        state: GuardianGraphState,
    ) -> StateUpdate:
        versions = state.get("versions") or {}
        links = load_policy_links_fn(versions)
        return {"policy_links": links}

    def classify_impacts(
        state: GuardianGraphState,
    ) -> StateUpdate:
        analysis = state.get("change_analysis") or {}
        links = state.get("policy_links") or []

        impacts = classify_impacts_fn(
            analysis,
            links,
        )

        return {"impacts": impacts}

    def validate_impacts(
        state: GuardianGraphState,
    ) -> StateUpdate:
        analysis = state.get("change_analysis") or {}
        impacts = state.get("impacts") or []
        versions = state.get("versions") or {}

        errors = validate_impacts_fn(
            analysis,
            impacts,
            versions,
        )

        if errors:
            return {
                "validation_errors": list(errors),
                "terminal_state": "NEEDS_HUMAN_REVIEW",
            }

        return {
            "validation_errors": [],
            "terminal_state": "VALID",
        }

    def persist_result(
        state: GuardianGraphState,
    ) -> StateUpdate:
        analysis = state.get("change_analysis") or {}
        impacts = state.get("impacts") or []
        versions = state.get("versions") or {}

        persisted = persist_result_fn(
            analysis,
            impacts,
            versions,
        )

        return {
            "persisted_result": persisted,
            "final_output": persisted,
            "terminal_state": "VALID",
        }

    def finish_review(
        state: GuardianGraphState,
    ) -> StateUpdate:
        return {
            "final_output": {
                "change_analysis": state.get("change_analysis") or {},
                "impacts": state.get("impacts") or [],
                "validation_errors": state.get("validation_errors") or [],
            },
            "terminal_state": "NEEDS_HUMAN_REVIEW",
        }

    def route_after_validation(
        state: GuardianGraphState,
    ) -> str:
        if state.get("validation_errors"):
            return "review"
        return "persist"

    graph = StateGraph(GuardianGraphState)

    graph.add_node("load_exact_versions", load_exact_versions)
    graph.add_node("deterministic_diff", deterministic_diff)
    graph.add_node("explain_changes", explain_changes)
    graph.add_node("load_policy_links", load_policy_links)
    graph.add_node("classify_impacts", classify_impacts)
    graph.add_node("validate_impacts", validate_impacts)
    graph.add_node("persist_result", persist_result)
    graph.add_node("finish_review", finish_review)

    graph.add_edge(START, "load_exact_versions")
    graph.add_edge("load_exact_versions", "deterministic_diff")
    graph.add_edge("deterministic_diff", "explain_changes")
    graph.add_edge("explain_changes", "load_policy_links")
    graph.add_edge("load_policy_links", "classify_impacts")
    graph.add_edge("classify_impacts", "validate_impacts")

    graph.add_conditional_edges(
        "validate_impacts",
        route_after_validation,
        {
            "persist": "persist_result",
            "review": "finish_review",
        },
    )

    graph.add_edge("persist_result", END)
    graph.add_edge("finish_review", END)

    return graph.compile()
