from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.graphs.learning import build_learning_graph
from app.learning.prompt import LEARNING_CANDIDATE_PROMPT
from app.learning.schemas import LearningCandidate


SanitizeTextFn = Callable[[str], str]


class LearningGraphError(ValueError):
    pass


def _model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def generate_learning_candidate_via_graph(
    *,
    case_id: UUID,
    case_facts: dict[str, Any],
    correction_summary: str,
    structured_diff: dict[str, Any],
    policy_payload: list[dict[str, Any]],
    scope: dict[str, list[str] | str],
    policy_refs: list[str],
    source_evidence: list[str],
    sanitize_text: SanitizeTextFn,
) -> LearningCandidate:
    """
    Run the approved-learning candidate stage through LangGraph.

    Database persistence and approval creation remain in the existing
    learning service. This graph only reasons over the already-verified
    completed-case correction and returns a validated/sanitized candidate.
    """

    def load_completed_case_fn(requested_case_id: str) -> dict[str, Any]:
        if str(case_id) != str(requested_case_id):
            raise LearningGraphError(
                "Graph case_id does not match the loaded case."
            )

        return {
            "case_id": str(case_id),
            "case_facts": case_facts,
            "correction_summary": correction_summary,
        }

    def compare_revisions_fn(
        _loaded_case: dict[str, Any],
    ) -> dict[str, Any]:
        return structured_diff

    def retrieve_current_policy_fn(
        _loaded_case: dict[str, Any],
        _comparison: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "policies": policy_payload,
            "policy_refs": policy_refs,
            "source_evidence": source_evidence,
            "scope": scope,
        }

    def draft_candidate_fn(
        _loaded_case: dict[str, Any],
        comparison: dict[str, Any],
        policy_context: dict[str, Any],
    ) -> dict[str, Any]:
        structured = _model().with_structured_output(
            LearningCandidate,
            method="function_calling",
        )
        chain = LEARNING_CANDIDATE_PROMPT | structured

        result = chain.invoke(
            {
                "case_scope": json.dumps(scope, indent=2),
                "correction_summary": correction_summary or "",
                "structured_diff": json.dumps(
                    comparison,
                    indent=2,
                    default=str,
                ),
                "policy_evidence": json.dumps(
                    policy_context.get("policies", []),
                    indent=2,
                    default=str,
                ),
            }
        )

        candidate = LearningCandidate.model_validate(result)

        # Deterministic authority comes from the service, not from the LLM.
        candidate.scope = scope
        candidate.policy_refs = policy_refs
        candidate.source_evidence = source_evidence

        return candidate.model_dump(mode="json")

    def sanitize_fn(
        candidate_payload: dict[str, Any],
    ) -> dict[str, Any]:
        candidate = LearningCandidate.model_validate(candidate_payload)
        sanitized = candidate.model_copy(deep=True)

        sanitized.situation = sanitize_text(candidate.situation)
        sanitized.recommended_action = sanitize_text(
            candidate.recommended_action
        )
        sanitized.rationale = sanitize_text(candidate.rationale)
        sanitized.conditions = [
            sanitize_text(item)
            for item in candidate.conditions
        ]
        sanitized.sensitive_data_removed = True

        return sanitized.model_dump(mode="json")

    def validate_scope_fn(
        candidate_payload: dict[str, Any],
        _loaded_case: dict[str, Any],
        policy_context: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        try:
            candidate = LearningCandidate.model_validate(
                candidate_payload
            )
        except Exception as exc:
            return [f"Learning candidate schema validation failed: {exc}"]

        expected_policy_refs = set(
            str(item)
            for item in policy_context.get("policy_refs", [])
        )
        actual_policy_refs = set(candidate.policy_refs)

        if actual_policy_refs != expected_policy_refs:
            errors.append(
                "Learning candidate policy_refs do not exactly match "
                "the current policy versions."
            )

        expected_evidence = set(
            str(item)
            for item in policy_context.get("source_evidence", [])
        )
        actual_evidence = set(candidate.source_evidence)

        if not actual_evidence.issubset(expected_evidence):
            errors.append(
                "Learning candidate cites source evidence outside "
                "the verified revised plan."
            )

        if candidate.scope != scope:
            errors.append(
                "Learning candidate scope differs from the "
                "deterministic case scope."
            )

        if not candidate.sensitive_data_removed:
            errors.append(
                "Learning candidate was not marked as sanitized."
            )

        if not candidate.situation.strip():
            errors.append("Learning candidate situation is empty.")

        if not candidate.recommended_action.strip():
            errors.append(
                "Learning candidate recommended_action is empty."
            )

        return errors

    graph = build_learning_graph(
        load_completed_case_fn=load_completed_case_fn,
        compare_revisions_fn=compare_revisions_fn,
        retrieve_current_policy_fn=retrieve_current_policy_fn,
        draft_candidate_fn=draft_candidate_fn,
        sanitize_fn=sanitize_fn,
        validate_scope_fn=validate_scope_fn,
    )

    result = graph.invoke(
        {
            "case_id": str(case_id),
            "correlation_id": str(case_id),
            "repair_count": 0,
        }
    )

    if result.get("terminal_state") == "NEEDS_HUMAN_REVIEW":
        errors = result.get("validation_errors") or []
        raise LearningGraphError(
            "Learning LangGraph candidate requires human review. "
            f"Errors: {'; '.join(errors)}"
        )

    final_output = result.get("final_output")
    if not final_output:
        raise LearningGraphError(
            "Learning LangGraph returned no final candidate."
        )

    return LearningCandidate.model_validate(final_output)
