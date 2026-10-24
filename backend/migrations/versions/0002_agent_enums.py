"""Agent workforce enum values and named CHECK constraints.

Adds the enum values from FINAL_PLAN / HANDOFF section 5.1 and rebuilds the
CHECK constraint of every enum column from the frozen lists below. Existing
constraints are found by column, not by name, because older databases carry
SQLAlchemy's class-named constraints (e.g. "resourcetype") or the manual
"ck_company_resources_status" patch. Every constraint is recreated as
ck_<table>_<column>, so running the rebuild again is safe.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


# Allowed values per "table.column" after this revision. A test compares
# these with app.enums, so an enum change without a migration fails CI.
ENUM_CHECKS = {
    "audit_events.actor_type": (
        "USER",
        "SYSTEM",
        "LLM",
        "N8N",
        "ML",
        "AGENT",
    ),
    "people.app_role": (
        "HR_MANAGER",
        "LINE_MANAGER",
        "IT_OWNER",
        "EMPLOYEE",
        "ADMIN",
    ),
    "people.employment_status": (
        "CANDIDATE",
        "ACTIVE",
        "DEPARTING",
        "INACTIVE",
    ),
    "access_events.alert_status": (
        "NONE",
        "OPEN",
        "CONFIRMED",
        "FALSE_POSITIVE",
        "CLOSED",
    ),
    "approvals.target_type": (
        "PLAN",
        "LEARNING",
        "POLICY_IMPACT",
        "HANDOVER",
    ),
    "approvals.status": (
        "PENDING",
        "APPROVED",
        "REJECTED",
    ),
    "cases.case_type": (
        "ONBOARDING",
        "OFFBOARDING",
        "ACCESS_REQUEST",
    ),
    "cases.status": (
        "NEW",
        "PLANNING",
        "PENDING_APPROVAL",
        "APPROVED",
        "EXECUTING",
        "COMPLETED",
        "FAILED",
        "HUMAN_REVIEW",
        "PAUSED",
        "CANCELLED",
    ),
    "cases.priority": (
        "LOW",
        "NORMAL",
        "HIGH",
    ),
    "policy_versions.status": (
        "DRAFT",
        "CURRENT",
        "ARCHIVED",
    ),
    "case_plans.status": (
        "DRAFT",
        "PENDING_APPROVAL",
        "APPROVED",
        "REJECTED",
        "SUPERSEDED",
        "STALE",
    ),
    "policy_changes.overall_risk": (
        "LOW",
        "MEDIUM",
        "HIGH",
    ),
    "policy_changes.status": (
        "ANALYZED",
        "REVIEWED",
        "RESOLVED",
    ),
    "policy_links.subject_type": (
        "PLAN",
        "LEARNING",
    ),
    "case_actions.action_type": (
        "CREATE",
        "ASSIGN",
        "DISABLE",
        "REVOKE",
        "REASSIGN",
        "REQUEST_RETURN",
        "DOWNSCOPE",
        "GRANT_TEMPORARY",
    ),
    "case_actions.resource_type": (
        "EMAIL_ACCOUNT",
        "GITHUB_ACCESS",
        "LAPTOP",
        "TRAINING",
        "WORK_ITEM",
        "KNOWLEDGE_DOCUMENT",
        "AI_AGENT",
        "AGENT_CREDENTIAL",
    ),
    "case_actions.status": (
        "PENDING",
        "DISPATCHED",
        "SUCCEEDED",
        "VERIFIED",
        "FAILED",
        "RETRYING",
        "HUMAN_REVIEW",
        "SKIPPED",
    ),
    "learning_records.trigger_type": (
        "PLAN_CORRECTION",
        "HANDOVER",
    ),
    "learning_records.status": (
        "PENDING_APPROVAL",
        "APPROVED",
        "REJECTED",
        "STALE",
    ),
    "policy_impacts.target_type": (
        "PLAN",
        "CASE",
        "LEARNING",
        "RESOURCE",
    ),
    "policy_impacts.risk_level": (
        "LOW",
        "MEDIUM",
        "HIGH",
    ),
    "policy_impacts.recommended_action": (
        "REGENERATE",
        "REVIEW",
        "MARK_STALE",
        "NO_ACTION",
    ),
    "policy_impacts.status": (
        "OPEN",
        "ACCEPTED",
        "REMEDIATING",
        "RESOLVED",
        "IGNORED",
    ),
    "company_resources.resource_type": (
        "EMAIL_ACCOUNT",
        "GITHUB_ACCESS",
        "LAPTOP",
        "TRAINING",
        "WORK_ITEM",
        "KNOWLEDGE_DOCUMENT",
        "AI_AGENT",
        "AGENT_CREDENTIAL",
    ),
    "company_resources.status": (
        "OPEN",
        "ACTIVE",
        "ASSIGNED",
        "DISABLED",
        "REVOKED",
        "RETURN_REQUESTED",
        "RETURNED",
        "REASSIGNED",
        "SUSPENDED",
        "EXPIRED",
    ),
}


# Python enum class behind each column, for the test above.
ENUM_CLASSES = {
    "audit_events.actor_type": "AuditActorType",
    "people.app_role": "AppRole",
    "people.employment_status": "EmploymentStatus",
    "access_events.alert_status": "AlertState",
    "approvals.target_type": "ApprovalTargetType",
    "approvals.status": "ApprovalState",
    "cases.case_type": "CaseType",
    "cases.status": "CaseState",
    "cases.priority": "CasePriority",
    "policy_versions.status": "PolicyState",
    "case_plans.status": "PlanState",
    "policy_changes.overall_risk": "RiskLevel",
    "policy_changes.status": "PolicyChangeState",
    "policy_links.subject_type": "PolicyLinkSubjectType",
    "case_actions.action_type": "ActionType",
    "case_actions.resource_type": "ResourceType",
    "case_actions.status": "ActionState",
    "learning_records.trigger_type": "LearningTriggerType",
    "learning_records.status": "LearningState",
    "policy_impacts.target_type": "PolicyImpactTargetType",
    "policy_impacts.risk_level": "RiskLevel",
    "policy_impacts.recommended_action": "ImpactRecommendedAction",
    "policy_impacts.status": "ImpactState",
    "company_resources.resource_type": "ResourceType",
    "company_resources.status": "ResourceState",
}


# Values introduced by this revision, removed again on downgrade.
ADDED_VALUES = {
    "ResourceType": ("AI_AGENT", "AGENT_CREDENTIAL"),
    "ActionType": ("DOWNSCOPE", "GRANT_TEMPORARY"),
    "ResourceState": ("SUSPENDED", "EXPIRED"),
    "CaseType": ("ACCESS_REQUEST",),
    "PolicyImpactTargetType": ("RESOURCE",),
    "AuditActorType": ("AGENT",),
}


def _drop_column_checks(table: str, column: str) -> None:
    names = op.get_bind().execute(
        text(
            """
            SELECT con.conname
            FROM pg_constraint AS con
            JOIN pg_attribute AS att
              ON att.attrelid = con.conrelid
             AND att.attnum = con.conkey[1]
            WHERE con.conrelid = to_regclass(:table)
              AND con.contype = 'c'
              AND array_length(con.conkey, 1) = 1
              AND att.attname = :column
            """
        ),
        {"table": f"public.{table}", "column": column},
    ).scalars().all()
    for name in names:
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{name}"')


def _rebuild_checks(checks: dict[str, tuple[str, ...]]) -> None:
    for key, values in checks.items():
        table, column = key.split(".")
        _drop_column_checks(table, column)
        allowed = ", ".join(f"'{value}'" for value in values)
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_{column} "
            f"CHECK ({column} IN ({allowed}))"
        )


def upgrade() -> None:
    _rebuild_checks(ENUM_CHECKS)


def downgrade() -> None:
    previous = {
        key: tuple(
            value
            for value in values
            if value not in ADDED_VALUES.get(ENUM_CLASSES[key], ())
        )
        for key, values in ENUM_CHECKS.items()
    }
    _rebuild_checks(previous)
