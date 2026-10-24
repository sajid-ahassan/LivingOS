from __future__ import annotations

from app.main import app
from app.scripts.demo_cli import build_parser
from app.scripts.reset_demo import reset_demo_data


EXPECTED_PATHS = {
    "/",
    "/health",
    "/cases",
    "/cases/{case_id}",
    "/cases/{case_id}/triage",
    "/cases/{case_id}/policy-context",
    "/cases/{case_id}/plan",
    "/plans/{plan_id}/submit",
    "/approvals/{approval_id}/decision",
    "/plans/{plan_id}/execute",
    "/plans/{plan_id}/retry",
    "/cases/{case_id}/offboarding/inventory",
    "/cases/{case_id}/offboarding/plan",
    "/cases/{case_id}/handover",
    "/handover-approvals/{approval_id}/decision",
    "/cases/{case_id}/learning/candidate",
    "/learning-approvals/{approval_id}/decision",
    "/learning/{learning_record_id}/index",
    "/learning/search",
    "/plans/{plan_id}/revise",
    "/audit/cases/{case_id}/timeline",
    "/audit/cases/{case_id}/coverage",
    "/access-events",
    "/security/alerts",
    "/access-events/{event_id}/review",
    "/mock/resources/apply",
    "/mock/resources/{resource_key}",
    "/mock/people/{person_id}/resources",
    "/policy-guardian/activate",
    "/policy-guardian/changes/{change_id}",
    "/policy-guardian/impacts/{impact_id}/regenerate",
    "/agents",
    "/agents/orphans",
    "/agents/{resource_key}",
    "/agents/{resource_key}/grants",
    "/workforce/graph",
    "/demo/mode",
}


def test_stage2_openapi_contains_expected_routes():
    spec = app.openapi()
    actual_paths = set(spec["paths"])

    missing = EXPECTED_PATHS - actual_paths
    assert not missing, f"Missing Stage 2 API paths: {sorted(missing)}"


def test_openapi_has_no_duplicate_operation_ids():
    spec = app.openapi()

    operation_ids: list[str] = []

    for operations in spec["paths"].values():
        for method, metadata in operations.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                continue

            operation_id = metadata.get("operationId")
            if operation_id:
                operation_ids.append(operation_id)

    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_metadata_is_stage2_ready():
    spec = app.openapi()

    assert spec["info"]["title"] == "LivingOps AI"
    assert spec["info"]["version"] == "0.2.0-stage2"
    assert "operations command center" in spec["info"]["description"].lower()


def test_critical_stage2_http_methods():
    spec = app.openapi()

    assert "post" in spec["paths"]["/cases"]
    assert "post" in spec["paths"]["/cases/{case_id}/plan"]
    assert "post" in spec["paths"]["/plans/{plan_id}/execute"]
    assert "post" in spec["paths"]["/plans/{plan_id}/retry"]

    assert "post" in spec["paths"]["/cases/{case_id}/offboarding/plan"]
    assert "post" in spec["paths"]["/cases/{case_id}/learning/candidate"]

    assert "post" in spec["paths"]["/policy-guardian/activate"]
    assert "post" in spec["paths"]["/access-events"]

    assert "get" in spec["paths"]["/audit/cases/{case_id}/timeline"]
    assert "get" in spec["paths"]["/audit/cases/{case_id}/coverage"]
    assert "get" in spec["paths"]["/security/alerts"]


def test_demo_cli_exposes_required_stage2_commands():
    parser = build_parser()

    help_text = parser.format_help()

    assert "LivingOps AI Stage 2 demo CLI" in help_text

    # Parse representative commands to protect the presentation interface
    # against accidental command removal.
    assert parser.parse_args(["health"]).command == "health"
    assert parser.parse_args(["seed"]).command == "seed"
    assert parser.parse_args(["reset"]).command == "reset"
    assert parser.parse_args(["endpoints"]).command == "endpoints"
    assert parser.parse_args(["alerts"]).command == "alerts"

    timeline = parser.parse_args(["timeline", "case-123"])
    assert timeline.command == "timeline"
    assert timeline.case_id == "case-123"

    change = parser.parse_args(["policy-change", "change-123"])
    assert change.command == "policy-change"
    assert change.change_id == "change-123"


def test_reset_demo_entrypoint_is_available():
    assert callable(reset_demo_data)
