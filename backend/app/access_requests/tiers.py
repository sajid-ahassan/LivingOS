"""Risk tiers for agent access requests (Agent Policy V1, rules 1, 3, 4, 5).

Rules decide the tier; the LLM only explains it to the approver. LOW is
approved automatically, HIGH waits for the IT Owner, DENY is refused with the
rule it breaks. Same request, same tier, every time.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.enums import EmploymentStatus
from app.models import Person
from app.policy_guardian.resource_rules import CONFIDENTIAL_REPOSITORIES


class RiskTier(StrEnum):
    LOW = "LOW"
    HIGH = "HIGH"
    DENY = "DENY"


READ_PERMISSIONS = {"read", "pull"}
WRITE_PERMISSIONS = {"write", "push"}
FORBIDDEN_PERMISSIONS = {"admin", "maintain", "production", "owner"}
FORBIDDEN_RESOURCE_MARKERS = ("prod", "production")

MAX_READ_MINUTES = 24 * 60    # Agent Policy rule 4
MAX_WRITE_MINUTES = 8 * 60    # Agent Policy rule 3


@dataclass(frozen=True)
class TierDecision:
    tier: RiskTier
    reasons: tuple[str, ...]
    policy_rule: str


def decide_tier(
    *,
    permission: str,
    resource: str,
    duration_minutes: int,
    sponsor: Person | None,
) -> TierDecision:
    permission = permission.strip().lower()
    resource = resource.strip().lower()
    denials: list[str] = []

    if permission in FORBIDDEN_PERMISSIONS or any(
        marker in resource for marker in FORBIDDEN_RESOURCE_MARKERS
    ):
        denials.append("production or administrator access is never self-service")
    if permission not in READ_PERMISSIONS | WRITE_PERMISSIONS | FORBIDDEN_PERMISSIONS:
        denials.append(f"unknown permission '{permission}'")
    if sponsor is None or sponsor.employment_status != EmploymentStatus.ACTIVE:
        denials.append("the agent has no active human sponsor")
    if duration_minutes < 1:
        denials.append("duration must be at least one minute")

    is_write = permission in WRITE_PERMISSIONS
    limit = MAX_WRITE_MINUTES if is_write else MAX_READ_MINUTES
    if duration_minutes > limit:
        denials.append(f"duration {duration_minutes} min is over the {limit} min limit")

    if denials:
        return TierDecision(RiskTier.DENY, tuple(denials), "AGENT-V1 rules 1, 3, 4, 5")

    confidential = resource in CONFIDENTIAL_REPOSITORIES
    if is_write or confidential:
        reasons = []
        if is_write:
            reasons.append("write access")
        if confidential:
            reasons.append(f"{resource} is a confidential repository")
        return TierDecision(RiskTier.HIGH, tuple(reasons), "AGENT-V1 rule 3")

    return TierDecision(
        RiskTier.LOW,
        ("read access to a non-confidential repository with an active sponsor",),
        "AGENT-V1 rule 4",
    )
