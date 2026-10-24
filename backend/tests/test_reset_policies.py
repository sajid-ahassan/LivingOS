from __future__ import annotations

from uuid import uuid4

import pytest

from app.enums import PolicyState
from app.scripts.reset_policies import (
    PolicyResetError,
    PolicyVersionRow,
    apply_policy_reset,
    plan_policy_reset,
)


def _row(code: str, number: int, status: PolicyState) -> PolicyVersionRow:
    return PolicyVersionRow(
        id=uuid4(),
        policy_code=code,
        version_number=number,
        status=status,
    )


class UntouchableDb:
    """Fails the test if the reset touches the database."""

    def __getattr__(self, name):
        raise AssertionError(f"database was used: {name}")


def test_clean_database_needs_no_reset():
    rows = [
        _row("ACCESS", 1, PolicyState.CURRENT),
        _row("EQUIPMENT", 1, PolicyState.CURRENT),
        _row("OFFBOARDING", 1, PolicyState.CURRENT),
        _row("AGENT", 1, PolicyState.CURRENT),
    ]
    plan = plan_policy_reset(rows)
    assert plan.is_noop
    assert len(plan.keep) == 4


def test_supabase_state_today_restores_access_v1():
    """Old test run: ACCESS V2 CURRENT, V1 ARCHIVED, AGENT not ingested."""
    v1 = _row("ACCESS", 1, PolicyState.ARCHIVED)
    v2 = _row("ACCESS", 2, PolicyState.CURRENT)
    rows = [
        v1,
        v2,
        _row("EQUIPMENT", 1, PolicyState.CURRENT),
        _row("OFFBOARDING", 1, PolicyState.CURRENT),
    ]
    plan = plan_policy_reset(rows)
    assert plan.remove == [v2]
    assert plan.restore == [v1]
    assert plan.not_ingested == ["AGENT"]


def test_after_rehearsal_v2_and_drafts_are_removed():
    v1 = _row("ACCESS", 1, PolicyState.ARCHIVED)
    v2 = _row("ACCESS", 2, PolicyState.CURRENT)
    v3_draft = _row("ACCESS", 3, PolicyState.DRAFT)
    plan = plan_policy_reset([v3_draft, v2, v1], codes=["ACCESS"])
    assert plan.remove == [v2, v3_draft]
    assert plan.restore == [v1]


def test_non_seed_policies_are_left_alone():
    other = _row("TRAVEL", 2, PolicyState.CURRENT)
    plan = plan_policy_reset(
        [_row("ACCESS", 1, PolicyState.CURRENT), other],
        codes=["ACCESS"],
    )
    assert plan.is_noop
    assert other not in plan.remove


def test_missing_v1_stops_the_reset():
    with pytest.raises(PolicyResetError, match="no V1"):
        plan_policy_reset([_row("ACCESS", 2, PolicyState.CURRENT)], codes=["ACCESS"])


def test_v1_without_qdrant_points_changes_nothing():
    plan = plan_policy_reset(
        [_row("ACCESS", 1, PolicyState.ARCHIVED), _row("ACCESS", 2, PolicyState.CURRENT)],
        codes=["ACCESS"],
    )
    with pytest.raises(PolicyResetError, match="no Qdrant points"):
        apply_policy_reset(UntouchableDb(), plan, count_points=lambda _id: 0)


def test_noop_plan_does_not_need_deletes():
    plan = plan_policy_reset([_row("ACCESS", 1, PolicyState.CURRENT)], codes=["ACCESS"])

    class FlushOnlyDb:
        def flush(self):
            pass

    counts = apply_policy_reset(FlushOnlyDb(), plan, count_points=lambda _id: 6)
    assert counts["policy_versions"] == 0
    assert counts["restored_v1"] == 0
