"""ISO/IEC 27001:2022 supporting-evidence report for one case.

Built only from what the system already recorded (plan, approvals, verified
actions, audit timestamps). It is evidence an auditor can check, not a
certification. Controls covered:

- 6.5  Responsibilities after termination: each access removal against the
       termination date, and whether it happened within 24 hours.
- 5.11 Return of assets: return requests, due dates, status.
- 5.18 Access rights: every change with its policy reason, approver, time
       and evidence IDs.
- 8.2  Privileged access rights: GitHub and agent credentials, with how the
       result was verified.
"""
from __future__ import annotations

import html
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ActionState, ActionType, ApprovalState, ResourceType
from app.models import Approval, AuditEvent, Case, CaseAction, CasePlan, Person


DHAKA = timezone(timedelta(hours=6))
ACCESS_TYPES = {
    ResourceType.EMAIL_ACCOUNT,
    ResourceType.GITHUB_ACCESS,
    ResourceType.AI_AGENT,
    ResourceType.AGENT_CREDENTIAL,
}
PRIVILEGED_TYPES = {
    ResourceType.GITHUB_ACCESS,
    ResourceType.AI_AGENT,
    ResourceType.AGENT_CREDENTIAL,
}
DISCLAIMER = (
    "Supporting evidence for ISO/IEC 27001:2022 audits, generated from "
    "LivingOps records. It is not a certification or an audit opinion."
)


class EvidenceNotFoundError(ValueError):
    pass


def termination_deadline(last_working_day: str | None) -> datetime | None:
    """End of the last working day, Dhaka time."""
    if not last_working_day:
        return None
    day = date.fromisoformat(str(last_working_day)[:10])
    return datetime.combine(day, time(23, 59, 59), tzinfo=DHAKA)


def removal_timing(verified_at: datetime | None, deadline: datetime | None) -> dict[str, Any]:
    if verified_at is None or deadline is None:
        return {"hours_after_termination": None, "within_24h": None}
    hours = round((verified_at - deadline).total_seconds() / 3600, 2)
    return {"hours_after_termination": hours, "within_24h": hours <= 24}


def _executed_plan(db: Session, case: Case) -> CasePlan | None:
    plans = list(
        db.scalars(
            select(CasePlan).where(CasePlan.case_id == case.id).order_by(CasePlan.revision.desc())
        )
    )
    for plan in plans:
        if any(action.status != ActionState.SKIPPED for action in plan.actions):
            return plan
    return plans[0] if plans else None


def _verified_at(db: Session, action: CaseAction) -> datetime | None:
    event = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.entity_id == action.id, AuditEvent.event_type == "ACTION_VERIFIED")
        .order_by(AuditEvent.occurred_at.desc())
        .limit(1)
    )
    return event.occurred_at if event else None


def _name(db: Session, person_id: UUID | None) -> str | None:
    person = db.get(Person, person_id) if person_id else None
    return person.name if person else None


def build_evidence(db: Session, case_id: UUID) -> dict[str, Any]:
    case = db.get(Case, case_id)
    if case is None:
        raise EvidenceNotFoundError(f"Case does not exist: {case_id}")
    plan = _executed_plan(db, case)
    if plan is None:
        raise EvidenceNotFoundError("The case has no plan yet.")

    approval = db.scalar(
        select(Approval)
        .where(Approval.target_id == plan.id, Approval.status == ApprovalState.APPROVED)
        .order_by(Approval.decided_at.desc())
        .limit(1)
    )
    approver = _name(db, approval.assigned_to) if approval else None
    approved_at = approval.decided_at.isoformat() if approval and approval.decided_at else None
    facts = case.case_facts or {}
    deadline = termination_deadline(facts.get("last_working_day"))

    actions = sorted(plan.actions, key=lambda a: int((a.requested_data or {}).get("sequence", 0)))
    rows = []
    for action in actions:
        data = action.requested_data or {}
        verified_at = _verified_at(db, action)
        verification = action.verification_data or {}
        rows.append({
            "sequence": int(data.get("sequence", 0)),
            "action_type": action.action_type,
            "resource_type": action.resource_type,
            "resource_key": data.get("resource_key"),
            "reason": data.get("reason"),
            "evidence_ids": data.get("evidence_ids") or [],
            "status": action.status.value,
            "verified_at": verified_at,
            "verified_by": verification.get("source"),
            "github_observed": verification.get("github_observed"),
            "parameters": data.get("parameters") or {},
        })

    def iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    control_6_5 = [
        {
            "resource_key": row["resource_key"],
            "action": row["action_type"].value,
            "verified_at": iso(row["verified_at"]),
            **removal_timing(row["verified_at"], deadline),
        }
        for row in rows
        if row["resource_type"] in ACCESS_TYPES
    ]
    control_5_11 = [
        {
            "resource_key": row["resource_key"],
            "due_date": row["parameters"].get("due_date"),
            "status": row["status"],
            "verified_at": iso(row["verified_at"]),
        }
        for row in rows
        if row["action_type"] == ActionType.REQUEST_RETURN
    ]
    control_5_18 = [
        {
            "sequence": row["sequence"],
            "action": row["action_type"].value,
            "resource_key": row["resource_key"],
            "policy_reason": row["reason"],
            "evidence_ids": row["evidence_ids"],
            "approved_by": approver,
            "approved_at": approved_at,
            "verified_at": iso(row["verified_at"]),
        }
        for row in rows
    ]
    control_8_2 = [
        {
            "resource_key": row["resource_key"],
            "resource_type": row["resource_type"].value,
            "action": row["action_type"].value,
            "status": row["status"],
            "verified_by": row["verified_by"],
            "github_observed": row["github_observed"],
        }
        for row in rows
        if row["resource_type"] in PRIVILEGED_TYPES
    ]

    removals = [item for item in control_6_5 if item["within_24h"] is not None]
    return {
        "disclaimer": DISCLAIMER,
        "company": "Nexora Labs (fictional demo company)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case": {
            "id": str(case.id),
            "type": case.case_type.value,
            "status": case.status.value,
            "subject": _name(db, case.subject_person_id),
            "opened_by": _name(db, case.created_by_id),
            "opened_at": iso(case.created_at),
            "last_working_day": facts.get("last_working_day"),
        },
        "plan": {
            "id": str(plan.id),
            "revision": plan.revision,
            "status": plan.status.value,
            "approved_by": approver,
            "approved_at": approved_at,
            "correction_summary": plan.correction_summary,
        },
        "summary": {
            "access_removals": len(control_6_5),
            "removals_within_24h": sum(1 for item in removals if item["within_24h"]),
            "all_actions_verified": all(row["status"] == ActionState.VERIFIED.value for row in rows),
        },
        "controls": {
            "6.5": control_6_5,
            "5.11": control_5_11,
            "5.18": control_5_18,
            "8.2": control_8_2,
        },
    }


CONTROL_TITLES = {
    "6.5": "Responsibilities after termination or change of employment",
    "5.11": "Return of assets",
    "5.18": "Access rights",
    "8.2": "Privileged access rights",
}


def _cell(value: Any) -> str:
    if value is None:
        return "&mdash;"
    if isinstance(value, bool):
        return "yes" if value else "<strong>no</strong>"
    if isinstance(value, (list, dict)):
        value = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
    return html.escape(str(value))


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='empty'>No records for this control in this case.</p>"
    headers = list(rows[0])
    head = "".join(f"<th>{html.escape(h.replace('_', ' '))}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_cell(row.get(h))}</td>" for h in headers) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(evidence: dict[str, Any]) -> str:
    case, plan, summary = evidence["case"], evidence["plan"], evidence["summary"]
    sections = "".join(
        f"<section><h2>{code} {html.escape(CONTROL_TITLES[code])}</h2>{_table(rows)}</section>"
        for code, rows in evidence["controls"].items()
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evidence report</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:32px;color:#111;background:#fff;line-height:1.45}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;margin:28px 0 8px;border-bottom:1px solid #ccc;padding-bottom:4px}}
.note{{background:#fff7e0;border:1px solid #e8c766;padding:10px 12px;border-radius:6px;font-size:13px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:14px}} dt{{color:#555}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}} th,td{{border:1px solid #ccc;padding:5px 7px;text-align:left;vertical-align:top}}
th{{background:#f2f2f2;text-transform:capitalize}} .empty{{color:#666;font-size:13px}}
@media print{{body{{margin:12mm}} .note{{break-inside:avoid}}}}
</style></head><body>
<h1>Access evidence report: {html.escape(str(case['subject']))}</h1>
<p>{html.escape(evidence['company'])} &middot; generated {html.escape(evidence['generated_at'])}</p>
<p class="note">{html.escape(evidence['disclaimer'])}</p>
<dl>
<dt>Case</dt><dd>{_cell(case['type'])} &middot; {_cell(case['status'])} &middot; {_cell(case['id'])}</dd>
<dt>Opened</dt><dd>{_cell(case['opened_by'])}, {_cell(case['opened_at'])}</dd>
<dt>Last working day</dt><dd>{_cell(case['last_working_day'])}</dd>
<dt>Approved plan</dt><dd>revision {_cell(plan['revision'])} by {_cell(plan['approved_by'])}, {_cell(plan['approved_at'])}</dd>
<dt>Manager correction</dt><dd>{_cell(plan['correction_summary'])}</dd>
<dt>Access removals within 24 h</dt><dd>{summary['removals_within_24h']} of {summary['access_removals']}</dd>
<dt>All actions verified</dt><dd>{_cell(summary['all_actions_verified'])}</dd>
</dl>
{sections}
</body></html>"""
