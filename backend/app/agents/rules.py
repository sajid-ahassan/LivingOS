from __future__ import annotations

from datetime import datetime, timezone

from app.enums import EmploymentStatus, ResourceState, ResourceType
from app.models import CompanyResource, Person


# Deterministic orphan rule (FINAL_PLAN, "AI agent as workforce"): an agent is
# an orphan when its sponsor is missing, leaving or gone, or its access expired.
ORPHAN_NO_SPONSOR = "NO_SPONSOR"
ORPHAN_SPONSOR_DEPARTING = "SPONSOR_DEPARTING"
ORPHAN_SPONSOR_INACTIVE = "SPONSOR_INACTIVE"
ORPHAN_EXPIRED = "EXPIRED"


RETIRED_AGENT_STATES = {
    ResourceState.REVOKED,
    ResourceState.DISABLED,
    ResourceState.EXPIRED,
}


def _parse_expiry(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        expires_at = value
    else:
        try:
            expires_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at


def orphan_reasons(
    agent: CompanyResource,
    sponsor: Person | None,
    now: datetime,
) -> list[str]:
    """Return why an agent is orphaned; an empty list means it is not."""
    if agent.resource_type != ResourceType.AI_AGENT:
        raise ValueError(f"{agent.resource_key} is not an AI_AGENT resource.")
    if agent.status in RETIRED_AGENT_STATES:
        return []

    reasons: list[str] = []
    if sponsor is None:
        reasons.append(ORPHAN_NO_SPONSOR)
    elif sponsor.employment_status == EmploymentStatus.DEPARTING:
        reasons.append(ORPHAN_SPONSOR_DEPARTING)
    elif sponsor.employment_status == EmploymentStatus.INACTIVE:
        reasons.append(ORPHAN_SPONSOR_INACTIVE)

    expires_at = _parse_expiry((agent.details_data or {}).get("expires_at"))
    if expires_at is not None and expires_at <= now:
        reasons.append(ORPHAN_EXPIRED)

    return reasons
