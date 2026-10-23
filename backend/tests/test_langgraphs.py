from __future__ import annotations

from app.graphs.guardian import build_guardian_graph
from app.graphs.learning import build_learning_graph
from app.graphs.offboarding import build_offboarding_graph
from app.graphs.onboarding import build_onboarding_graph


def test_onboarding_graph_valid_first_pass():
    graph = build_onboarding_graph(
        load_case_fn=lambda case_id: {
            "case_id": case_id,
            "case_type": "ONBOARDING",
        },
        retrieve_context_fn=lambda facts: {
            "policy": "current",
        },
        generate_plan_fn=lambda facts, retrieval: {
            "summary": "Valid onboarding plan",
            "actions": [],
        },
        validate_plan_fn=lambda draft, retrieval: [],
        repair_plan_fn=lambda draft, errors, retrieval: draft,
    )

    result = graph.invoke(
        {
            "case_id": "case-1",
            "correlation_id": "case-1",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "VALID"
    assert result["repair_count"] == 0
    assert result["final_output"]["summary"] == "Valid onboarding plan"


def test_onboarding_graph_repairs_once():
    validation_calls = {"count": 0}

    def validate(draft, retrieval):
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            return ["draft invalid"]
        return []

    graph = build_onboarding_graph(
        load_case_fn=lambda case_id: {"case_id": case_id},
        retrieve_context_fn=lambda facts: {"policy": "current"},
        generate_plan_fn=lambda facts, retrieval: {
            "summary": "Initial",
            "actions": [],
        },
        validate_plan_fn=validate,
        repair_plan_fn=lambda draft, errors, retrieval: {
            "summary": "Repaired",
            "actions": [],
        },
    )

    result = graph.invoke(
        {
            "case_id": "case-2",
            "correlation_id": "case-2",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "VALID"
    assert result["repair_count"] == 1
    assert result["final_output"]["summary"] == "Repaired"


def test_onboarding_graph_stops_after_one_failed_repair():
    graph = build_onboarding_graph(
        load_case_fn=lambda case_id: {"case_id": case_id},
        retrieve_context_fn=lambda facts: {"policy": "current"},
        generate_plan_fn=lambda facts, retrieval: {
            "summary": "Invalid",
            "actions": [],
        },
        validate_plan_fn=lambda draft, retrieval: ["still invalid"],
        repair_plan_fn=lambda draft, errors, retrieval: {
            "summary": "Still invalid",
            "actions": [],
        },
    )

    result = graph.invoke(
        {
            "case_id": "case-3",
            "correlation_id": "case-3",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "NEEDS_HUMAN_REVIEW"
    assert result["repair_count"] == 1
    assert result["validation_errors"]


def test_learning_graph_valid_candidate():
    graph = build_learning_graph(
        load_completed_case_fn=lambda case_id: {
            "case_id": case_id,
            "status": "COMPLETED",
        },
        compare_revisions_fn=lambda facts: {
            "changed": ["access rule"],
        },
        retrieve_current_policy_fn=lambda facts, comparison: {
            "policy_refs": ["policy-v2"],
        },
        draft_candidate_fn=lambda facts, comparison, policy_context: {
            "situation": "A reusable corrected access-planning situation.",
            "conditions": ["Engineering onboarding"],
            "recommended_action": "Use the corrected access rule.",
            "rationale": "The manager correction matches current policy.",
            "scope": {"case_types": ["ONBOARDING"]},
            "policy_refs": ["policy-v2"],
            "source_evidence": ["ev-1"],
            "sensitive_data_removed": False,
            "confidence": 0.9,
        },
        sanitize_fn=lambda candidate: {
            **candidate,
            "sensitive_data_removed": True,
        },
        validate_scope_fn=lambda candidate, facts, policy_context: [],
    )

    result = graph.invoke(
        {
            "case_id": "case-learning",
            "correlation_id": "case-learning",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "VALID"
    assert result["final_output"]["sensitive_data_removed"] is True


def test_learning_graph_routes_invalid_candidate_to_review():
    graph = build_learning_graph(
        load_completed_case_fn=lambda case_id: {"case_id": case_id},
        compare_revisions_fn=lambda facts: {"changed": ["x"]},
        retrieve_current_policy_fn=lambda facts, comparison: {
            "policy_refs": ["policy-v2"],
        },
        draft_candidate_fn=lambda facts, comparison, policy_context: {
            "candidate": "draft",
        },
        sanitize_fn=lambda candidate: candidate,
        validate_scope_fn=lambda candidate, facts, policy_context: [
            "scope conflict"
        ],
    )

    result = graph.invoke(
        {
            "case_id": "case-learning-bad",
            "correlation_id": "case-learning-bad",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "NEEDS_HUMAN_REVIEW"
    assert result["validation_errors"] == ["scope conflict"]


def test_guardian_graph_valid_analysis():
    graph = build_guardian_graph(
        load_exact_versions_fn=lambda old_id, new_id: {
            "old_version_id": old_id,
            "new_version_id": new_id,
            "old_hash": "a",
            "new_hash": "b",
        },
        deterministic_diff_fn=lambda versions: {
            "added_lines": ["new rule"],
            "removed_lines": ["old rule"],
            "unified_diff": "-old rule\n+new rule",
        },
        explain_changes_fn=lambda versions, diff: {
            "summary": {
                "overall_risk": "HIGH",
            },
            "deterministic": diff,
        },
        load_policy_links_fn=lambda versions: [
            {
                "policy_link_id": "link-1",
                "subject_type": "PLAN",
                "subject_id": "plan-1",
            }
        ],
        classify_impacts_fn=lambda analysis, links: [
            {
                "target_type": "PLAN",
                "target_id": "plan-1",
            }
        ],
        validate_impacts_fn=lambda analysis, impacts, versions: [],
        persist_result_fn=lambda analysis, impacts, versions: {
            "analysis": analysis,
            "impacts": impacts,
        },
    )

    result = graph.invoke(
        {
            "old_version_id": "old-v1",
            "new_version_id": "new-v2",
            "correlation_id": "guardian-test",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "VALID"
    assert result["final_output"]["impacts"][0]["target_id"] == "plan-1"


def test_guardian_graph_invalid_impacts_require_review():
    graph = build_guardian_graph(
        load_exact_versions_fn=lambda old_id, new_id: {
            "old_version_id": old_id,
            "new_version_id": new_id,
        },
        deterministic_diff_fn=lambda versions: {
            "added_lines": ["new rule"],
            "removed_lines": [],
            "unified_diff": "+new rule",
        },
        explain_changes_fn=lambda versions, diff: {
            "summary": {"overall_risk": "MEDIUM"},
            "deterministic": diff,
        },
        load_policy_links_fn=lambda versions: [],
        classify_impacts_fn=lambda analysis, links: [
            {
                "target_type": "PLAN",
                "target_id": "invented-plan",
            }
        ],
        validate_impacts_fn=lambda analysis, impacts, versions: [
            "impact target is not policy-linked"
        ],
        persist_result_fn=lambda analysis, impacts, versions: {
            "analysis": analysis,
            "impacts": impacts,
        },
    )

    result = graph.invoke(
        {
            "old_version_id": "old-v1",
            "new_version_id": "new-v2",
            "correlation_id": "guardian-test-bad",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "NEEDS_HUMAN_REVIEW"
    assert result["validation_errors"]


def test_offboarding_graph_valid_without_repair():
    graph = build_offboarding_graph(
        load_case_fn=lambda case_id: {
            "case_id": case_id,
            "case_type": "OFFBOARDING",
        },
        inventory_resources_fn=lambda facts: [
            {"resource_key": "github:user"}
        ],
        retrieve_context_fn=lambda facts, resources: {
            "policy": "current"
        },
        generate_plan_fn=lambda facts, resources, retrieval: {
            "summary": "Valid offboarding plan",
            "revocations": [],
            "asset_returns": [],
            "reassignments": [],
            "targeted_questions": [],
        },
        validate_plan_fn=lambda draft, resources, retrieval: [],
        generate_questions_fn=lambda facts, resources, retrieval, draft: [
            "What open work needs handover?",
            "Which operational context should the successor know?",
        ],
        validate_questions_fn=lambda questions, facts, resources: [],
        repair_plan_fn=lambda draft, errors, retrieval: draft,
        repair_questions_fn=lambda current, errors, retrieval: current,
    )

    result = graph.invoke(
        {
            "case_id": "case-offboarding",
            "correlation_id": "case-offboarding",
            "repair_count": 0,
        }
    )

    assert result["terminal_state"] == "VALID"
    assert result["repair_count"] == 0
    assert result["final_output"] is not None
