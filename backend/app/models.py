from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    ActionState,
    ActionType,
    AlertState,
    AppRole,
    ApprovalState,
    ApprovalTargetType,
    AuditActorType,
    CasePriority,
    CaseState,
    CaseType,
    EmploymentStatus,
    ImpactRecommendedAction,
    ImpactState,
    LearningState,
    LearningTriggerType,
    PlanState,
    PolicyChangeState,
    PolicyImpactTargetType,
    PolicyLinkSubjectType,
    PolicyState,
    ResourceState,
    ResourceType,
    RiskLevel,
)


def string_enum(enum_class: type, length: int) -> SqlEnum:
    """Store Python enums as validated VARCHAR values, not PostgreSQL enum types."""
    return SqlEnum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=length,
    )


class Person(Base):
    __tablename__ = "people"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    app_role: Mapped[AppRole] = mapped_column(
        string_enum(AppRole, 32),
        nullable=False,
    )
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        string_enum(EmploymentStatus, 24),
        nullable=False,
    )
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    manager_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    manager: Mapped[Person | None] = relationship(
        remote_side=[id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list[Person]] = relationship(
        back_populates="manager",
    )
    subject_cases: Mapped[list[Case]] = relationship(
        back_populates="subject_person",
        foreign_keys="Case.subject_person_id",
    )
    created_cases: Mapped[list[Case]] = relationship(
        back_populates="created_by",
        foreign_keys="Case.created_by_id",
    )
    requested_approvals: Mapped[list[Approval]] = relationship(
        back_populates="requester",
        foreign_keys="Approval.requested_by",
    )
    assigned_approvals: Mapped[list[Approval]] = relationship(
        back_populates="assignee",
        foreign_keys="Approval.assigned_to",
    )
    uploaded_policies: Mapped[list[PolicyVersion]] = relationship(
        back_populates="uploader",
    )
    resolved_policy_impacts: Mapped[list[PolicyImpact]] = relationship(
        back_populates="resolver",
        foreign_keys="PolicyImpact.resolved_by",
    )
    resources: Mapped[list[CompanyResource]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    access_events: Mapped[list[AccessEvent]] = relationship(
        back_populates="person",
        foreign_keys="AccessEvent.person_id",
        cascade="all, delete-orphan",
    )
    reviewed_access_events: Mapped[list[AccessEvent]] = relationship(
        back_populates="reviewer",
        foreign_keys="AccessEvent.reviewed_by",
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_type: Mapped[CaseType] = mapped_column(
        string_enum(CaseType, 24),
        nullable=False,
    )
    subject_person_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[CaseState] = mapped_column(
        string_enum(CaseState, 32),
        nullable=False,
        default=CaseState.NEW,
        index=True,
    )
    priority: Mapped[CasePriority] = mapped_column(
        string_enum(CasePriority, 16),
        nullable=False,
        default=CasePriority.NORMAL,
    )
    case_facts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    subject_person: Mapped[Person] = relationship(
        back_populates="subject_cases",
        foreign_keys=[subject_person_id],
    )
    created_by: Mapped[Person] = relationship(
        back_populates="created_cases",
        foreign_keys=[created_by_id],
    )
    plans: Mapped[list[CasePlan]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
    actions: Mapped[list[CaseAction]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
    learning_records: Mapped[list[LearningRecord]] = relationship(
        back_populates="source_case",
    )


class CasePlan(Base):
    __tablename__ = "case_plans"

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "revision",
            name="uq_case_plans_case_revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PlanState] = mapped_column(
        string_enum(PlanState, 32),
        nullable=False,
        default=PlanState.DRAFT,
        index=True,
    )
    plan_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    parent_plan_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("case_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    correction_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    case: Mapped[Case] = relationship(back_populates="plans")
    parent_plan: Mapped[CasePlan | None] = relationship(
        remote_side=[id],
        back_populates="child_revisions",
    )
    child_revisions: Mapped[list[CasePlan]] = relationship(
        back_populates="parent_plan",
    )
    actions: Mapped[list[CaseAction]] = relationship(
        back_populates="plan",
    )
    learning_records: Mapped[list[LearningRecord]] = relationship(
        back_populates="source_plan",
    )


class CaseAction(Base):
    __tablename__ = "case_actions"

    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 2",
            name="ck_case_actions_attempt_count",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("case_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action_type: Mapped[ActionType] = mapped_column(
        string_enum(ActionType, 40),
        nullable=False,
    )
    resource_type: Mapped[ResourceType] = mapped_column(
        string_enum(ResourceType, 40),
        nullable=False,
    )
    requested_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ActionState] = mapped_column(
        string_enum(ActionState, 32),
        nullable=False,
        default=ActionState.PENDING,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
    )
    n8n_execution_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verification_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    case: Mapped[Case] = relationship(back_populates="actions")
    plan: Mapped[CasePlan] = relationship(back_populates="actions")
    affected_resources: Mapped[list[CompanyResource]] = relationship(
        back_populates="source_action",
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    target_type: Mapped[ApprovalTargetType] = mapped_column(
        string_enum(ApprovalTargetType, 32),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    requested_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_to: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ApprovalState] = mapped_column(
        string_enum(ApprovalState, 24),
        nullable=False,
        default=ApprovalState.PENDING,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    requester: Mapped[Person] = relationship(
        back_populates="requested_approvals",
        foreign_keys=[requested_by],
    )
    assignee: Mapped[Person] = relationship(
        back_populates="assigned_approvals",
        foreign_keys=[assigned_to],
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    __table_args__ = (
        UniqueConstraint(
            "policy_code",
            "version_number",
            name="uq_policy_version_number",
        ),
        UniqueConstraint(
            "policy_code",
            "content_hash",
            name="uq_policy_content_hash",
        ),
        Index(
            "uq_policy_versions_one_current",
            "policy_code",
            unique=True,
            postgresql_where=text("status = 'CURRENT'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    policy_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PolicyState] = mapped_column(
        string_enum(PolicyState, 16),
        nullable=False,
        default=PolicyState.DRAFT,
    )
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    uploaded_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    uploader: Mapped[Person] = relationship(
        back_populates="uploaded_policies",
    )
    links: Mapped[list[PolicyLink]] = relationship(
        back_populates="policy_version",
    )
    changes_as_old_version: Mapped[list[PolicyChange]] = relationship(
        back_populates="old_version",
        foreign_keys="PolicyChange.old_version_id",
    )
    changes_as_new_version: Mapped[list[PolicyChange]] = relationship(
        back_populates="new_version",
        foreign_keys="PolicyChange.new_version_id",
    )


class PolicyLink(Base):
    __tablename__ = "policy_links"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[PolicyLinkSubjectType] = mapped_column(
        string_enum(PolicyLinkSubjectType, 24),
        nullable=False,
    )
    subject_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    use_reason: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    policy_version: Mapped[PolicyVersion] = relationship(
        back_populates="links",
    )


class LearningRecord(Base):
    __tablename__ = "learning_records"

    __table_args__ = (
        Index(
            "ix_learning_records_scope_gin",
            "scope",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source_case_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_plan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("case_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trigger_type: Mapped[LearningTriggerType] = mapped_column(
        string_enum(LearningTriggerType, 32),
        nullable=False,
    )
    status: Mapped[LearningState] = mapped_column(
        string_enum(LearningState, 24),
        nullable=False,
        default=LearningState.PENDING_APPROVAL,
        index=True,
    )
    candidate_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    memory_text: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    qdrant_point_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_case: Mapped[Case] = relationship(
        back_populates="learning_records",
    )
    source_plan: Mapped[CasePlan] = relationship(
        back_populates="learning_records",
    )


class PolicyChange(Base):
    __tablename__ = "policy_changes"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    policy_code: Mapped[str] = mapped_column(String(50), nullable=False)
    old_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    new_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    diff_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_risk: Mapped[RiskLevel] = mapped_column(
        string_enum(RiskLevel, 16),
        nullable=False,
    )
    status: Mapped[PolicyChangeState] = mapped_column(
        string_enum(PolicyChangeState, 24),
        nullable=False,
        default=PolicyChangeState.ANALYZED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    old_version: Mapped[PolicyVersion] = relationship(
        back_populates="changes_as_old_version",
        foreign_keys=[old_version_id],
    )
    new_version: Mapped[PolicyVersion] = relationship(
        back_populates="changes_as_new_version",
        foreign_keys=[new_version_id],
    )
    impacts: Mapped[list[PolicyImpact]] = relationship(
        back_populates="policy_change",
        cascade="all, delete-orphan",
    )


class PolicyImpact(Base):
    __tablename__ = "policy_impacts"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    policy_change_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("policy_changes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[PolicyImpactTargetType] = mapped_column(
        string_enum(PolicyImpactTargetType, 24),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        string_enum(RiskLevel, 16),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[ImpactRecommendedAction] = mapped_column(
        string_enum(ImpactRecommendedAction, 40),
        nullable=False,
    )
    status: Mapped[ImpactState] = mapped_column(
        string_enum(ImpactState, 24),
        nullable=False,
        default=ImpactState.OPEN,
        index=True,
    )
    resolved_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    policy_change: Mapped[PolicyChange] = relationship(
        back_populates="impacts",
    )
    resolver: Mapped[Person | None] = relationship(
        back_populates="resolved_policy_impacts",
        foreign_keys=[resolved_by],
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    actor_type: Mapped[AuditActorType] = mapped_column(
        string_enum(AuditActorType, 24),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    before_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
        index=True,
    )


class CompanyResource(Base):
    __tablename__ = "company_resources"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    person_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[ResourceType] = mapped_column(
        string_enum(ResourceType, 40),
        nullable=False,
    )
    resource_key: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        unique=True,
    )
    status: Mapped[ResourceState] = mapped_column(
        string_enum(ResourceState, 32),
        nullable=False,
    )
    details_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    source_action_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("case_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    person: Mapped[Person] = relationship(back_populates="resources")
    source_action: Mapped[CaseAction | None] = relationship(
        back_populates="affected_resources",
    )


class AccessEvent(Base):
    __tablename__ = "access_events"

    __table_args__ = (
        CheckConstraint(
            "anomaly_score >= 0 AND anomaly_score <= 1",
            name="ck_access_events_anomaly_score",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    person_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    features_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    alert_status: Mapped[AlertState] = mapped_column(
        string_enum(AlertState, 24),
        nullable=False,
        default=AlertState.NONE,
        index=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    person: Mapped[Person] = relationship(
        back_populates="access_events",
        foreign_keys=[person_id],
    )
    reviewer: Mapped[Person | None] = relationship(
        back_populates="reviewed_access_events",
        foreign_keys=[reviewed_by],
    )