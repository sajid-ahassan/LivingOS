"""Baseline: the schema as it stood at commit 5877e00 (stage 3 complete).

The DDL below is frozen PostgreSQL output of the SQLAlchemy models at that
commit. A fresh database gets the full schema from `alembic upgrade head`.
A database built earlier by Base.metadata.create_all already has this schema
and is only marked with `alembic stamp 0001` (no DDL runs).

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""
from __future__ import annotations

from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


TABLES = (
    "audit_events",
    "people",
    "access_events",
    "approvals",
    "cases",
    "policy_versions",
    "case_plans",
    "policy_changes",
    "policy_links",
    "case_actions",
    "learning_records",
    "policy_impacts",
    "company_resources",
)


STATEMENTS = (
    """
    CREATE TABLE audit_events (
        id UUID NOT NULL,
        occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        actor_type VARCHAR(24) NOT NULL,
        actor_id UUID,
        event_type VARCHAR(80) NOT NULL,
        entity_type VARCHAR(32) NOT NULL,
        entity_id UUID NOT NULL,
        before_data JSONB,
        after_data JSONB,
        evidence_data JSONB,
        correlation_id UUID NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT auditactortype CHECK (actor_type IN ('USER', 'SYSTEM', 'LLM', 'N8N', 'ML'))
    )
    """,
    """
    CREATE INDEX ix_audit_events_correlation_id ON audit_events (correlation_id)
    """,
    """
    CREATE INDEX ix_audit_events_occurred_at ON audit_events (occurred_at)
    """,
    """
    CREATE TABLE people (
        id UUID NOT NULL,
        name VARCHAR(160) NOT NULL,
        email VARCHAR(255) NOT NULL,
        app_role VARCHAR(32) NOT NULL,
        employment_status VARCHAR(24) NOT NULL,
        department VARCHAR(80) NOT NULL,
        job_title VARCHAR(120) NOT NULL,
        manager_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (email),
        CONSTRAINT approle CHECK (app_role IN ('HR_MANAGER', 'LINE_MANAGER', 'IT_OWNER', 'EMPLOYEE', 'ADMIN')),
        CONSTRAINT employmentstatus CHECK (employment_status IN ('CANDIDATE', 'ACTIVE', 'DEPARTING', 'INACTIVE')),
        FOREIGN KEY(manager_id) REFERENCES people (id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE access_events (
        id UUID NOT NULL,
        person_id UUID NOT NULL,
        event_time TIMESTAMP WITH TIME ZONE NOT NULL,
        source VARCHAR(120) NOT NULL,
        destination VARCHAR(120) NOT NULL,
        event_type VARCHAR(40) NOT NULL,
        success BOOLEAN NOT NULL,
        features_data JSONB NOT NULL,
        anomaly_score FLOAT NOT NULL,
        alert_status VARCHAR(24) NOT NULL,
        reviewed_by UUID,
        review_comment TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT ck_access_events_anomaly_score CHECK (anomaly_score >= 0 AND anomaly_score <= 1),
        FOREIGN KEY(person_id) REFERENCES people (id) ON DELETE CASCADE,
        CONSTRAINT alertstate CHECK (alert_status IN ('NONE', 'OPEN', 'CONFIRMED', 'FALSE_POSITIVE', 'CLOSED')),
        FOREIGN KEY(reviewed_by) REFERENCES people (id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX ix_access_events_alert_status ON access_events (alert_status)
    """,
    """
    CREATE INDEX ix_access_events_event_time ON access_events (event_time)
    """,
    """
    CREATE TABLE approvals (
        id UUID NOT NULL,
        target_type VARCHAR(32) NOT NULL,
        target_id UUID NOT NULL,
        requested_by UUID NOT NULL,
        assigned_to UUID NOT NULL,
        status VARCHAR(24) NOT NULL,
        comment TEXT,
        requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        decided_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT approvaltargettype CHECK (target_type IN ('PLAN', 'LEARNING', 'POLICY_IMPACT', 'HANDOVER')),
        FOREIGN KEY(requested_by) REFERENCES people (id) ON DELETE RESTRICT,
        FOREIGN KEY(assigned_to) REFERENCES people (id) ON DELETE RESTRICT,
        CONSTRAINT approvalstate CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
    )
    """,
    """
    CREATE INDEX ix_approvals_status ON approvals (status)
    """,
    """
    CREATE TABLE cases (
        id UUID NOT NULL,
        case_type VARCHAR(24) NOT NULL,
        subject_person_id UUID NOT NULL,
        created_by_id UUID NOT NULL,
        status VARCHAR(32) NOT NULL,
        priority VARCHAR(16) NOT NULL,
        case_facts JSONB NOT NULL,
        failure_reason TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT casetype CHECK (case_type IN ('ONBOARDING', 'OFFBOARDING')),
        FOREIGN KEY(subject_person_id) REFERENCES people (id) ON DELETE RESTRICT,
        FOREIGN KEY(created_by_id) REFERENCES people (id) ON DELETE RESTRICT,
        CONSTRAINT casestate CHECK (status IN ('NEW', 'PLANNING', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING', 'COMPLETED', 'FAILED', 'HUMAN_REVIEW', 'PAUSED', 'CANCELLED')),
        CONSTRAINT casepriority CHECK (priority IN ('LOW', 'NORMAL', 'HIGH'))
    )
    """,
    """
    CREATE INDEX ix_cases_status ON cases (status)
    """,
    """
    CREATE TABLE policy_versions (
        id UUID NOT NULL,
        policy_code VARCHAR(50) NOT NULL,
        title VARCHAR(180) NOT NULL,
        version_number INTEGER NOT NULL,
        status VARCHAR(16) NOT NULL,
        department VARCHAR(80) NOT NULL,
        effective_from DATE NOT NULL,
        content_text TEXT NOT NULL,
        content_hash CHAR(64) NOT NULL,
        uploaded_by UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_policy_version_number UNIQUE (policy_code, version_number),
        CONSTRAINT uq_policy_content_hash UNIQUE (policy_code, content_hash),
        CONSTRAINT policystate CHECK (status IN ('DRAFT', 'CURRENT', 'ARCHIVED')),
        FOREIGN KEY(uploaded_by) REFERENCES people (id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE UNIQUE INDEX uq_policy_versions_one_current ON policy_versions (policy_code) WHERE status = 'CURRENT'
    """,
    """
    CREATE TABLE case_plans (
        id UUID NOT NULL,
        case_id UUID NOT NULL,
        revision INTEGER NOT NULL,
        status VARCHAR(32) NOT NULL,
        plan_data JSONB NOT NULL,
        summary TEXT NOT NULL,
        parent_plan_id UUID,
        correction_summary TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT uq_case_plans_case_revision UNIQUE (case_id, revision),
        FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE,
        CONSTRAINT planstate CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SUPERSEDED', 'STALE')),
        FOREIGN KEY(parent_plan_id) REFERENCES case_plans (id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX ix_case_plans_status ON case_plans (status)
    """,
    """
    CREATE TABLE policy_changes (
        id UUID NOT NULL,
        policy_code VARCHAR(50) NOT NULL,
        old_version_id UUID NOT NULL,
        new_version_id UUID NOT NULL,
        diff_data JSONB NOT NULL,
        overall_risk VARCHAR(16) NOT NULL,
        status VARCHAR(24) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(old_version_id) REFERENCES policy_versions (id) ON DELETE RESTRICT,
        FOREIGN KEY(new_version_id) REFERENCES policy_versions (id) ON DELETE RESTRICT,
        CONSTRAINT risklevel CHECK (overall_risk IN ('LOW', 'MEDIUM', 'HIGH')),
        CONSTRAINT policychangestate CHECK (status IN ('ANALYZED', 'REVIEWED', 'RESOLVED'))
    )
    """,
    """
    CREATE TABLE policy_links (
        id UUID NOT NULL,
        policy_version_id UUID NOT NULL,
        subject_type VARCHAR(24) NOT NULL,
        subject_id UUID NOT NULL,
        use_reason VARCHAR(80) NOT NULL,
        evidence_ids JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(policy_version_id) REFERENCES policy_versions (id) ON DELETE RESTRICT,
        CONSTRAINT policylinksubjecttype CHECK (subject_type IN ('PLAN', 'LEARNING'))
    )
    """,
    """
    CREATE INDEX ix_policy_links_policy_version_id ON policy_links (policy_version_id)
    """,
    """
    CREATE TABLE case_actions (
        id UUID NOT NULL,
        case_id UUID NOT NULL,
        plan_id UUID NOT NULL,
        action_type VARCHAR(40) NOT NULL,
        resource_type VARCHAR(40) NOT NULL,
        requested_data JSONB NOT NULL,
        status VARCHAR(32) NOT NULL,
        idempotency_key VARCHAR(120) NOT NULL,
        n8n_execution_id VARCHAR(120),
        attempt_count INTEGER DEFAULT '0' NOT NULL,
        result_data JSONB,
        verification_data JSONB,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        CONSTRAINT ck_case_actions_attempt_count CHECK (attempt_count >= 0 AND attempt_count <= 2),
        FOREIGN KEY(case_id) REFERENCES cases (id) ON DELETE CASCADE,
        FOREIGN KEY(plan_id) REFERENCES case_plans (id) ON DELETE RESTRICT,
        CONSTRAINT actiontype CHECK (action_type IN ('CREATE', 'ASSIGN', 'DISABLE', 'REVOKE', 'REASSIGN', 'REQUEST_RETURN')),
        CONSTRAINT resourcetype CHECK (resource_type IN ('EMAIL_ACCOUNT', 'GITHUB_ACCESS', 'LAPTOP', 'TRAINING', 'WORK_ITEM', 'KNOWLEDGE_DOCUMENT')),
        CONSTRAINT actionstate CHECK (status IN ('PENDING', 'DISPATCHED', 'SUCCEEDED', 'VERIFIED', 'FAILED', 'RETRYING', 'HUMAN_REVIEW', 'SKIPPED')),
        UNIQUE (idempotency_key)
    )
    """,
    """
    CREATE INDEX ix_case_actions_status ON case_actions (status)
    """,
    """
    CREATE TABLE learning_records (
        id UUID NOT NULL,
        source_case_id UUID NOT NULL,
        source_plan_id UUID NOT NULL,
        trigger_type VARCHAR(32) NOT NULL,
        status VARCHAR(24) NOT NULL,
        candidate_data JSONB NOT NULL,
        memory_text TEXT NOT NULL,
        scope JSONB NOT NULL,
        qdrant_point_id UUID,
        stale_reason TEXT,
        content_hash CHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(source_case_id) REFERENCES cases (id) ON DELETE RESTRICT,
        FOREIGN KEY(source_plan_id) REFERENCES case_plans (id) ON DELETE RESTRICT,
        CONSTRAINT learningtriggertype CHECK (trigger_type IN ('PLAN_CORRECTION', 'HANDOVER')),
        CONSTRAINT learningstate CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'STALE'))
    )
    """,
    """
    CREATE INDEX ix_learning_records_content_hash ON learning_records (content_hash)
    """,
    """
    CREATE INDEX ix_learning_records_scope_gin ON learning_records USING gin (scope)
    """,
    """
    CREATE INDEX ix_learning_records_status ON learning_records (status)
    """,
    """
    CREATE TABLE policy_impacts (
        id UUID NOT NULL,
        policy_change_id UUID NOT NULL,
        target_type VARCHAR(24) NOT NULL,
        target_id UUID NOT NULL,
        risk_level VARCHAR(16) NOT NULL,
        explanation TEXT NOT NULL,
        recommended_action VARCHAR(40) NOT NULL,
        status VARCHAR(24) NOT NULL,
        resolved_by UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(policy_change_id) REFERENCES policy_changes (id) ON DELETE CASCADE,
        CONSTRAINT policyimpacttargettype CHECK (target_type IN ('PLAN', 'CASE', 'LEARNING')),
        CONSTRAINT risklevel CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
        CONSTRAINT impactrecommendedaction CHECK (recommended_action IN ('REGENERATE', 'REVIEW', 'MARK_STALE', 'NO_ACTION')),
        CONSTRAINT impactstate CHECK (status IN ('OPEN', 'ACCEPTED', 'REMEDIATING', 'RESOLVED', 'IGNORED')),
        FOREIGN KEY(resolved_by) REFERENCES people (id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX ix_policy_impacts_status ON policy_impacts (status)
    """,
    """
    CREATE TABLE company_resources (
        id UUID NOT NULL,
        person_id UUID NOT NULL,
        resource_type VARCHAR(40) NOT NULL,
        resource_key VARCHAR(160) NOT NULL,
        status VARCHAR(32) NOT NULL,
        details_data JSONB NOT NULL,
        source_action_id UUID,
        idempotency_key VARCHAR(120) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(person_id) REFERENCES people (id) ON DELETE CASCADE,
        CONSTRAINT resourcetype CHECK (resource_type IN ('EMAIL_ACCOUNT', 'GITHUB_ACCESS', 'LAPTOP', 'TRAINING', 'WORK_ITEM', 'KNOWLEDGE_DOCUMENT')),
        UNIQUE (resource_key),
        CONSTRAINT resourcestate CHECK (status IN ('OPEN', 'ACTIVE', 'ASSIGNED', 'DISABLED', 'REVOKED', 'RETURN_REQUESTED', 'RETURNED', 'REASSIGNED')),
        FOREIGN KEY(source_action_id) REFERENCES case_actions (id) ON DELETE SET NULL,
        UNIQUE (idempotency_key)
    )
    """,
)


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
