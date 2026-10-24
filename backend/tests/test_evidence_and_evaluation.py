from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.evaluation.metrics import guardian_accuracy, guardian_scenarios
from app.evidence.explanation import LESSON_EVIDENCE, POLICY_EVIDENCE, policy_clauses
from app.evidence.report import (
    DHAKA,
    DISCLAIMER,
    removal_timing,
    render_html,
    termination_deadline,
)


SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"
ACCESS_V1 = (SEED_DIR / "access_policy_v1.md").read_text(encoding="utf-8")
ACCESS_V2 = (SEED_DIR / "access_policy_v2.md").read_text(encoding="utf-8")


# Why panel


def test_policy_text_splits_into_numbered_clauses():
    clauses = policy_clauses(ACCESS_V2)
    assert [clause.number for clause in clauses] == list(range(1, 9))
    assert clauses[6].text.startswith("An AI agent may hold write access")


def test_evidence_ids_are_classified():
    assert POLICY_EVIDENCE.match("POL-ACCESS-V1-C0")["code"] == "ACCESS"
    assert POLICY_EVIDENCE.match("POL-AGENT-V12-C3")["version"] == "12"
    assert LESSON_EVIDENCE.match("MEM-0b1f6a2e-1111-4c2d-9e3f-aaaaaaaaaaaa-C0")
    assert not POLICY_EVIDENCE.match("MEM-x-C0")


# ISO 27001 control 6.5 timing


def test_termination_is_end_of_last_working_day_in_dhaka():
    deadline = termination_deadline("2026-12-26")
    assert deadline == datetime(2026, 12, 26, 23, 59, 59, tzinfo=DHAKA)
    assert termination_deadline(None) is None


def test_removal_before_or_within_a_day_passes_later_fails():
    deadline = termination_deadline("2026-12-26")
    before = removal_timing(deadline - timedelta(hours=5), deadline)
    assert before == {"hours_after_termination": -5.0, "within_24h": True}
    late = removal_timing(deadline + timedelta(hours=30), deadline)
    assert late["within_24h"] is False
    assert removal_timing(None, deadline)["within_24h"] is None


def _evidence(reason: str) -> dict:
    return {
        "disclaimer": DISCLAIMER,
        "company": "Nexora Labs (fictional demo company)",
        "generated_at": datetime(2026, 12, 26, tzinfo=timezone.utc).isoformat(),
        "case": {"id": "c1", "type": "OFFBOARDING", "status": "COMPLETED", "subject": "Arif Hossain",
                 "opened_by": "Farhana Islam", "opened_at": None, "last_working_day": "2026-12-26"},
        "plan": {"id": "p1", "revision": 2, "status": "APPROVED", "approved_by": "Nabil Chowdhury",
                 "approved_at": None, "correction_summary": "Keep the bot read-only."},
        "summary": {"access_removals": 1, "removals_within_24h": 1, "all_actions_verified": True},
        "controls": {
            "6.5": [{"resource_key": "github:aurora:arif", "action": "REVOKE",
                     "verified_at": None, "hours_after_termination": -3.0, "within_24h": True}],
            "5.11": [],
            "5.18": [{"sequence": 1, "action": "REVOKE", "resource_key": "github:aurora:arif",
                      "policy_reason": reason, "evidence_ids": ["POL-ACCESS-V1-C0"],
                      "approved_by": "Nabil Chowdhury", "approved_at": None, "verified_at": None}],
            "8.2": [],
        },
    }


def test_report_states_it_is_not_a_certification():
    page = render_html(_evidence("Access ends on the final working day."))
    assert "not a certification" in page
    assert "6.5 Responsibilities after termination" in page
    assert "1 of 1" in page
    assert "No records for this control" in page


def test_report_escapes_stored_text():
    page = render_html(_evidence("<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


# Evaluation: Guardian accuracy on seeded scenarios


def test_guardian_finds_every_seeded_impact_and_nothing_else():
    result = guardian_accuracy(ACCESS_V1, ACCESS_V2)
    assert result == {
        "n_scenarios": len(guardian_scenarios()),
        "expected_impacts": 2,
        "recall_pct": 100.0,
        "false_impacts": 0,
    }


def test_guardian_reports_honestly_when_rules_are_absent():
    result = guardian_accuracy(ACCESS_V1, ACCESS_V1)
    assert result["recall_pct"] == 0.0
    assert result["false_impacts"] == 0
