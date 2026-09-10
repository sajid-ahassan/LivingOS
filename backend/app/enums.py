from enum import StrEnum


class AppRole(StrEnum):
    HR_MANAGER = "HR_MANAGER"
    LINE_MANAGER = "LINE_MANAGER"
    IT_OWNER = "IT_OWNER"
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"


class EmploymentStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    DEPARTING = "DEPARTING"
    INACTIVE = "INACTIVE"


class CaseType(StrEnum):
    ONBOARDING = "ONBOARDING"
    OFFBOARDING = "OFFBOARDING"


class CasePriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class CaseState(StrEnum):
    NEW = "NEW"
    PLANNING = "PLANNING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class PlanState(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    STALE = "STALE"


class ActionType(StrEnum):
    CREATE = "CREATE"
    ASSIGN = "ASSIGN"
    DISABLE = "DISABLE"
    REVOKE = "REVOKE"
    REASSIGN = "REASSIGN"
    REQUEST_RETURN = "REQUEST_RETURN"


class ResourceType(StrEnum):
    EMAIL_ACCOUNT = "EMAIL_ACCOUNT"
    GITHUB_ACCESS = "GITHUB_ACCESS"
    LAPTOP = "LAPTOP"
    TRAINING = "TRAINING"
    WORK_ITEM = "WORK_ITEM"
    KNOWLEDGE_DOCUMENT = "KNOWLEDGE_DOCUMENT"


class ActionState(StrEnum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    SUCCEEDED = "SUCCEEDED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    SKIPPED = "SKIPPED"


class ApprovalTargetType(StrEnum):
    PLAN = "PLAN"
    LEARNING = "LEARNING"
    POLICY_IMPACT = "POLICY_IMPACT"
    HANDOVER = "HANDOVER"


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PolicyState(StrEnum):
    DRAFT = "DRAFT"
    CURRENT = "CURRENT"
    ARCHIVED = "ARCHIVED"


class PolicyLinkSubjectType(StrEnum):
    PLAN = "PLAN"
    LEARNING = "LEARNING"


class LearningTriggerType(StrEnum):
    PLAN_CORRECTION = "PLAN_CORRECTION"
    HANDOVER = "HANDOVER"


class LearningState(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PolicyChangeState(StrEnum):
    ANALYZED = "ANALYZED"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"


class PolicyImpactTargetType(StrEnum):
    PLAN = "PLAN"
    CASE = "CASE"
    LEARNING = "LEARNING"


class ImpactRecommendedAction(StrEnum):
    REGENERATE = "REGENERATE"
    REVIEW = "REVIEW"
    MARK_STALE = "MARK_STALE"
    NO_ACTION = "NO_ACTION"


class ImpactState(StrEnum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class AuditActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    LLM = "LLM"
    N8N = "N8N"
    ML = "ML"


class ResourceState(StrEnum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    ASSIGNED = "ASSIGNED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"
    REASSIGNED = "REASSIGNED"


class AlertState(StrEnum):
    NONE = "NONE"
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    CLOSED = "CLOSED"
