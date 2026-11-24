"""Approved lessons reach the planner only as advisory, policy-backed context."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.enums import ActionType, LearningState, PolicyState, ResourceType
from app.evaluation.lesson_reuse import _outcome
from app.learning import lessons as lesson_module
from app.learning.lessons import (
    LessonContext,
    credential_permission_from_diff,
    format_lessons,
    is_lesson_evidence,
    lesson_is_usable,
    offboarding_lesson_query,
    retrieve_offboarding_lessons,
)
from app.offboarding.graph_runner import _validate_execution_plan
from app.offboarding.rules import derive_agent_credential_actions
from app.planning.validation import policy_first_errors
from app.rag.learning_memory import MemorySearchResult

from test_agent_rules import (
    ACCESS_EVIDENCE,
    AGENT_EVIDENCE,
    AGENT_KEY,
    CREDENTIAL_KEY,
    NABIL,
    FakeDb,
    _action,
    _ai_version,
    _credential_actions,
    _offboarding_case,
    _offboarding_plan,
    _policy_context,
    _resources,
)


LESSON_ID = uuid4()
LESSON = f"MEM-{LESSON_ID}-C0"


def _record(status=LearningState.APPROVED, stale_reason=None, point=True):
    return SimpleNamespace(
        id=LESSON_ID,
        status=status,
        stale_reason=stale_reason,
        qdrant_point_id=uuid4() if point else None,
        candidate_data={},
    )


class LessonDb:
    """get() returns the lesson record; scalars() returns its policy statuses."""

    def __init__(self, record, policy_statuses=(PolicyState.CURRENT,)):
        self.record = record
        self.policy_statuses = list(policy_statuses)

    def get(self, _model, _id):
        return self.record

    def scalars(self, _query):
        return iter(self.policy_statuses)


def _hit(score=0.8, learning_id=LESSON_ID, text="Reassign release bots read-only."):
    return MemorySearchResult(
        evidence_id=f"MEM-{learning_id}-C0",
        learning_id=learning_id,
        trigger_type="PLAN_CORRECTION",
        text=text,
        score=score,
        policy_version_ids=[],
        scope={},
    )


def _retrieve(monkeypatch, db, hits=None, error=None):
    def fake_search(**_kwargs):
        if error:
            raise error
        return hits or []

    monkeypatch.setattr("app.rag.learning_memory.search_learning_memory", fake_search)
    return retrieve_offboarding_lessons(
        db, department="ENGINEERING", job_title="Engineer", resources=_resources()
    )


# Policy first ---------------------------------------------------------------

def test_lesson_ids_are_recognised():
    assert is_lesson_evidence(LESSON)
    assert not is_lesson_evidence(ACCESS_EVIDENCE)


def test_step_citing_only_a_lesson_is_rejected():
    action = _action(1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY, evidence=[LESSON])
    assert policy_first_errors(action)
    backed = _action(
        1, ActionType.REVOKE, ResourceType.AI_AGENT, AGENT_KEY,
        evidence=[ACCESS_EVIDENCE, LESSON],
    )
    assert policy_first_errors(backed) == []


def _graph_errors(plan, lesson_ids):
    context = _policy_context()
    return _validate_execution_plan(
        FakeDb(), _offboarding_case(), plan, _resources(),
        {item.evidence_id for item in context.evidence}, context, lesson_ids,
    )


READ_LESSON = LessonContext(LESSON, LESSON_ID, "Keep release bots read-only.", "read")


def _lesson_plan(agent_evidence=(ACCESS_EVIDENCE, AGENT_EVIDENCE, LESSON)):
    """What the model writes: the agent decision only, citing the lesson."""
    agent = _action(
        2, ActionType.REASSIGN, ResourceType.AI_AGENT, AGENT_KEY, NABIL,
        evidence=list(agent_evidence),
    )
    return _offboarding_plan(_ai_version()[:1], [agent])


def _derived(plan, lessons=(READ_LESSON,)):
    plan = derive_agent_credential_actions(plan, _resources(), lessons)
    for sequence, action in enumerate([*plan.revocations, *plan.reassignments], start=1):
        action.sequence = sequence
    return plan


def test_graph_accepts_a_retrieved_lesson_next_to_policy():
    assert _graph_errors(_derived(_lesson_plan()), {LESSON}) == []


def test_graph_rejects_a_lesson_that_was_not_retrieved():
    errors = _graph_errors(_derived(_lesson_plan()), set())
    assert any("unavailable evidence" in error for error in errors)


# Credential derivation ------------------------------------------------------

def test_cited_lesson_applies_its_recorded_downscope_by_rule():
    [credential] = _credential_actions(_derived(_lesson_plan()))
    assert credential.action_type == ActionType.DOWNSCOPE
    assert credential.requested_data == {
        "successor_person_id": str(NABIL.id),
        "permission": "read",
    }
    assert LESSON in credential.evidence_ids
    assert ACCESS_EVIDENCE in credential.evidence_ids


def test_uncited_lesson_changes_nothing():
    plan = _derived(_lesson_plan((ACCESS_EVIDENCE, AGENT_EVIDENCE)))
    [credential] = _credential_actions(plan)
    assert credential.action_type == ActionType.REASSIGN


def test_lesson_without_recorded_downscope_keeps_rotation():
    plain = LessonContext(LESSON, LESSON_ID, "Hand bots to the manager.")
    [credential] = _credential_actions(_derived(_lesson_plan(), (plain,)))
    assert credential.action_type == ActionType.REASSIGN


def test_model_written_credential_downscope_is_still_replaced():
    plan = _lesson_plan((ACCESS_EVIDENCE, AGENT_EVIDENCE))
    credential = _action(
        3, ActionType.DOWNSCOPE, ResourceType.AGENT_CREDENTIAL, CREDENTIAL_KEY, NABIL,
        evidence=[ACCESS_EVIDENCE, AGENT_EVIDENCE, LESSON],
    )
    plan.reassignments.append(credential)
    [derived] = _credential_actions(_derived(plan))
    assert derived.action_type == ActionType.REASSIGN


def test_recorded_permission_is_read_from_the_correction_diff():
    diff = {
        "added": [],
        "removed": [],
        "changed": [
            {
                "before": {"resource_type": "AGENT_CREDENTIAL", "action_type": "REASSIGN"},
                "after": {
                    "resource_type": "AGENT_CREDENTIAL",
                    "action_type": "DOWNSCOPE",
                    "requested_data": {"permission": "read"},
                },
            }
        ],
    }
    assert credential_permission_from_diff(diff) == "read"
    assert credential_permission_from_diff({"changed": []}) is None
    assert credential_permission_from_diff(None) is None


# What reaches the planner ---------------------------------------------------

def test_only_approved_current_indexed_lessons_are_usable():
    assert lesson_is_usable(LessonDb(_record()), _record()) is True
    assert lesson_is_usable(LessonDb(None), None) is False
    assert lesson_is_usable(LessonDb(None), _record(status=LearningState.STALE)) is False
    assert lesson_is_usable(LessonDb(None), _record(status=LearningState.REJECTED)) is False
    assert lesson_is_usable(LessonDb(None), _record(stale_reason="Policy changed")) is False
    assert lesson_is_usable(LessonDb(None), _record(point=False)) is False
    archived = LessonDb(None, (PolicyState.CURRENT, PolicyState.ARCHIVED))
    assert lesson_is_usable(archived, _record()) is False


def test_retrieval_rechecks_every_hit_in_postgres(monkeypatch):
    assert [l.evidence_id for l in _retrieve(monkeypatch, LessonDb(_record()), [_hit()])] == [LESSON]
    stale = LessonDb(_record(status=LearningState.STALE))
    assert _retrieve(monkeypatch, stale, [_hit()]) == []
    assert _retrieve(monkeypatch, LessonDb(None), [_hit()]) == []


def test_retrieval_drops_unrelated_hits(monkeypatch):
    low = lesson_module.LESSON_MIN_SCORE - 0.01
    assert _retrieve(monkeypatch, LessonDb(_record()), [_hit(score=low)]) == []


def test_retrieval_failure_never_blocks_planning(monkeypatch):
    assert _retrieve(monkeypatch, LessonDb(_record()), error=RuntimeError("down")) == []


def test_lesson_query_is_deterministic():
    first = offboarding_lesson_query("ENGINEERING", "Engineer", _resources())
    assert first == offboarding_lesson_query("ENGINEERING", "Engineer", list(reversed(_resources())))
    assert "Aurora Release Bot" in first


def test_prompt_section_says_when_no_lesson_applies():
    assert format_lessons([]) == "No approved lessons apply to this case."
    text = format_lessons([LessonContext(LESSON, LESSON_ID, "Keep it read-only.")])
    assert LESSON in text and "Keep it read-only." in text


# Evaluation scoring ---------------------------------------------------------

def test_outcome_matches_only_reassign_with_read_only_credential():
    result = _outcome(_derived(_lesson_plan()), AGENT_KEY, CREDENTIAL_KEY)
    assert result["matches_correction"] is True
    assert result["lesson_cited"] is True
    assert result["policy_cited_every_step"] is True

    rotated = _derived(_lesson_plan((ACCESS_EVIDENCE, AGENT_EVIDENCE)))
    assert _outcome(rotated, AGENT_KEY, CREDENTIAL_KEY)["matches_correction"] is False
