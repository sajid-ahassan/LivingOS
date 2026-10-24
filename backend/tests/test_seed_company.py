from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.agents.service import build_agent_summary, build_workforce_graph
from app.enums import EmploymentStatus, ResourceType
from app.models import CompanyResource, Person
from app.offboarding.rules import allowed_offboarding_actions
from app.scripts.seed_company import (
    CONFIDENTIAL_TRAINING,
    NABIL_ID,
    all_person_ids,
    build_company,
)
from app.scripts.seed_demo import ARIF_ID, PEOPLE as STORY_PEOPLE


# Day of the final; every orphan count below must hold on stage.
FINAL_DAY = datetime(2026, 12, 26, 10, 0, tzinfo=timezone.utc)
SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def _company():
    people, resources = build_company()
    return (
        [Person(**values) for values in people],
        [CompanyResource(**values) for values in resources],
    )


def _summaries():
    people, resources = _company()
    by_id = {person.id: person for person in people}
    return [
        build_agent_summary(resource, by_id.get(resource.person_id), FINAL_DAY)
        for resource in resources
        if resource.resource_type == ResourceType.AI_AGENT
    ]


def test_company_is_identical_on_every_run():
    assert build_company() == build_company()


def test_company_size_matches_plan():
    people, resources = build_company()
    agents = [r for r in resources if r["resource_type"] == ResourceType.AI_AGENT]
    assert 80 <= len(people) <= 100
    assert 20 <= len(agents) <= 30
    assert {p["department"] for p in people} == {
        "ENGINEERING", "PRODUCT", "DESIGN", "SALES",
        "SUPPORT", "FINANCE", "PEOPLE", "IT_SECURITY",
    }


def test_some_people_are_leaving_or_gone():
    statuses = Counter(p["employment_status"] for p in build_company()[0])
    assert statuses[EmploymentStatus.DEPARTING] >= 3
    assert statuses[EmploymentStatus.INACTIVE] >= 3


def test_story_characters_keep_their_ids():
    people = {p["id"]: p for p in build_company()[0]}
    for story_person in STORY_PEOPLE:
        assert people[story_person["id"]] == story_person


def test_keys_and_emails_are_unique():
    people, resources = build_company()
    assert len({p["email"] for p in people}) == len(people)
    assert len({r["resource_key"] for r in resources}) == len(resources)
    assert len({r["idempotency_key"] for r in resources}) == len(resources)


def test_everyone_has_a_manager_inside_the_company():
    people = build_company()[0]
    ids = {p["id"] for p in people}
    assert all(p["manager_id"] is None or p["manager_id"] in ids for p in people)


def test_people_hold_three_to_six_resources():
    people, resources = build_company()
    counts = Counter(
        r["person_id"]
        for r in resources
        if r["resource_type"] not in {ResourceType.AI_AGENT, ResourceType.AGENT_CREDENTIAL}
    )
    candidates = {
        p["id"] for p in people if p["employment_status"] == EmploymentStatus.CANDIDATE
    }
    for person in people:
        if person["id"] in candidates:
            # Amina and Rafi are onboarded during the demo.
            assert counts[person["id"]] == 0
        else:
            assert 3 <= counts[person["id"]] <= 6, person["name"]


def test_nabil_has_no_confidential_training():
    resources = build_company()[1]
    nabil_training = [
        r for r in resources
        if r["person_id"] == NABIL_ID
        and (r["details_data"] or {}).get("catalog_key") == CONFIDENTIAL_TRAINING
    ]
    assert nabil_training == []


def test_every_agent_has_its_credential_with_the_same_sponsor():
    resources = build_company()[1]
    by_key = {r["resource_key"]: r for r in resources}
    for agent in (r for r in resources if r["resource_type"] == ResourceType.AI_AGENT):
        credential = by_key[agent["details_data"]["credential_key"]]
        assert credential["resource_type"] == ResourceType.AGENT_CREDENTIAL
        assert credential["person_id"] == agent["person_id"]
        assert credential["details_data"]["agent_key"] == agent["resource_key"]
        assert "mcp_api_key_hash" not in agent["details_data"]


def test_preset_orphans_show_red_on_first_load():
    summaries = _summaries()
    orphans = [s for s in summaries if s.orphan]
    preset = [s for s in orphans if s.sponsor_id != ARIF_ID]
    arif_agents = [s for s in summaries if s.sponsor_id == ARIF_ID]

    assert 3 <= len(preset) <= 4
    assert {reason for s in preset for reason in s.orphan_reasons} == {
        "SPONSOR_INACTIVE", "SPONSOR_DEPARTING", "EXPIRED",
    }
    assert len(arif_agents) == 2
    assert all(s.orphan_reasons == ["SPONSOR_DEPARTING"] for s in arif_agents)


def test_arif_inventory_includes_both_bots_and_credentials():
    _, resources = _company()
    arif = [r for r in resources if r.person_id == ARIF_ID]
    keys = {r.resource_key for r in arif}
    assert {
        "agent:aurora-release-bot",
        "credential:aurora-release-bot",
        "agent:aurora-test-triage-bot",
        "credential:aurora-test-triage-bot",
    } <= keys
    agent_resources = [
        r for r in arif
        if r.resource_type in {ResourceType.AI_AGENT, ResourceType.AGENT_CREDENTIAL}
    ]
    assert all(allowed_offboarding_actions(r) for r in agent_resources)


def test_release_bot_matches_the_hero_story():
    summary = next(s for s in _summaries() if s.resource_key == "agent:aurora-release-bot")
    assert summary.sponsor_id == ARIF_ID
    assert summary.platform == "n8n"
    assert summary.risk_tier == "HIGH"
    assert summary.scopes == [
        {"system": "github", "resource": "aurora", "permission": "write"}
    ]


def test_reset_covers_every_seeded_person():
    people = build_company()[0]
    assert all_person_ids() == {p["id"] for p in people}


def test_workforce_graph_links_people_and_agents():
    people, resources = _company()
    graph = build_workforce_graph(people, resources, FINAL_DAY)

    assert len(graph.people) == len(people)
    assert len(graph.agents) == sum(
        r.resource_type == ResourceType.AI_AGENT for r in resources
    )
    sponsor_edges = [e for e in graph.edges if e.kind == "SPONSOR"]
    manager_edges = [e for e in graph.edges if e.kind == "MANAGER"]
    assert len(sponsor_edges) == len(graph.agents)
    assert len(manager_edges) == sum(p.manager_id is not None for p in people)
    assert sum(agent.orphan for agent in graph.agents) == 5

    arif = next(node for node in graph.people if node.id == ARIF_ID)
    # Email, GitHub, laptop, work item, runbook; agents are drawn separately.
    assert arif.access_count == 5


def test_workforce_graph_is_stable_between_calls():
    people, resources = _company()
    first = build_workforce_graph(people, resources, FINAL_DAY)
    second = build_workforce_graph(list(reversed(people)), list(reversed(resources)), FINAL_DAY)
    assert first == second


def test_agent_policy_has_the_six_agreed_rules():
    text = (SEED_DIR / "agent_policy_v1.md").read_text(encoding="utf-8")
    assert "Policy code: AGENT" in text
    rules = re.findall(r"^\d+\. ", text, flags=re.MULTILINE)
    assert len(rules) == 6
    assert "production or administrator access" in text
