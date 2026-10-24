"""Deterministic re-check of live agent access after a policy change.

A completed case is never reopened, but the access it granted keeps living.
When a new policy version adds one of the clauses below, Policy Guardian
re-evaluates every live agent resource that was granted under the old version
and reports a RESOURCE impact for each breach. No LLM is involved: the same
data always gives the same impacts, so the demo repeats exactly.

A rule applies only when its clause is new in this version (present in the
new text, absent from the old), so re-activating unrelated changes never
re-flags old findings.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.enums import (
    ImpactRecommendedAction,
    ResourceState,
    ResourceType,
    RiskLevel,
)
from app.models import CompanyResource, Person


CONFIDENTIAL_TRAINING = "SECURITY-CONFIDENTIAL"
CONFIDENTIAL_REPOSITORIES = {"aurora"}
LIVE_STATES = {ResourceState.ACTIVE, ResourceState.ASSIGNED, ResourceState.SUSPENDED}
COMPLETED_TRAINING_STATES = {ResourceState.ACTIVE, ResourceState.ASSIGNED}

RULE_CONFIDENTIAL_WRITE = "AGENT_WRITE_NEEDS_SPONSOR_TRAINING"
RULE_SPONSOR_RECERTIFY = "SPONSOR_CHANGE_NEEDS_RECERTIFICATION"


@dataclass(frozen=True)
class ResourceContext:
    resource: CompanyResource
    sponsor: Person | None
    sponsor_training: frozenset[str]


@dataclass(frozen=True)
class ResourceFinding:
    rule_id: str
    resource: CompanyResource
    risk_level: RiskLevel
    recommended_action: ImpactRecommendedAction
    explanation: str


@dataclass(frozen=True)
class ResourceRule:
    rule_id: str
    clause_marker: str
    check: Callable[[ResourceContext], ResourceFinding | None]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _sponsor_name(context: ResourceContext) -> str:
    return context.sponsor.name if context.sponsor else "no sponsor"


def _check_confidential_write(context: ResourceContext) -> ResourceFinding | None:
    resource = context.resource
    if resource.resource_type != ResourceType.AGENT_CREDENTIAL:
        return None
    details = resource.details_data or {}
    repository = details.get("repository") or (details.get("github") or {}).get("repo")
    if details.get("permission") != "write" or repository not in CONFIDENTIAL_REPOSITORIES:
        return None
    if CONFIDENTIAL_TRAINING in context.sponsor_training:
        return None
    return ResourceFinding(
        rule_id=RULE_CONFIDENTIAL_WRITE,
        resource=resource,
        risk_level=RiskLevel.HIGH,
        recommended_action=ImpactRecommendedAction.REGENERATE,
        explanation=(
            f"{resource.resource_key} has write access to the confidential "
            f"{repository} repository, but its sponsor ({_sponsor_name(context)}) "
            f"has no {CONFIDENTIAL_TRAINING} training. Downscope it to read-only."
        ),
    )


def _check_sponsor_recertification(context: ResourceContext) -> ResourceFinding | None:
    resource = context.resource
    if resource.resource_type != ResourceType.AI_AGENT:
        return None
    details = resource.details_data or {}
    if not details.get("previous_person_id"):
        return None
    recertified_for = details.get("recertified_for_sponsor")
    if recertified_for and recertified_for == str(resource.person_id):
        return None
    return ResourceFinding(
        rule_id=RULE_SPONSOR_RECERTIFY,
        resource=resource,
        risk_level=RiskLevel.MEDIUM,
        recommended_action=ImpactRecommendedAction.REVIEW,
        explanation=(
            f"{details.get('agent_name') or resource.resource_key} changed sponsor "
            f"to {_sponsor_name(context)} and the IT Owner has not re-certified "
            "its access."
        ),
    )


RESOURCE_RULES = (
    ResourceRule(
        rule_id=RULE_CONFIDENTIAL_WRITE,
        clause_marker=(
            "may hold write access to a confidential repository only while its "
            "sponsor has completed confidential security training"
        ),
        check=_check_confidential_write,
    ),
    ResourceRule(
        rule_id=RULE_SPONSOR_RECERTIFY,
        clause_marker="the it owner must re-certify the agent's access",
        check=_check_sponsor_recertification,
    ),
)


def newly_added_rules(
    old_text: str,
    new_text: str,
    rules: Iterable[ResourceRule] = RESOURCE_RULES,
) -> list[ResourceRule]:
    old, new = _normalized(old_text), _normalized(new_text)
    return [
        rule
        for rule in rules
        if _normalized(rule.clause_marker) in new
        and _normalized(rule.clause_marker) not in old
    ]


def evaluate_resources(
    rules: Iterable[ResourceRule],
    contexts: Iterable[ResourceContext],
) -> list[ResourceFinding]:
    rules = list(rules)
    findings = []
    for context in contexts:
        if context.resource.status not in LIVE_STATES:
            continue
        for rule in rules:
            finding = rule.check(context)
            if finding is not None:
                findings.append(finding)
    return sorted(findings, key=lambda f: (f.rule_id, f.resource.resource_key))
