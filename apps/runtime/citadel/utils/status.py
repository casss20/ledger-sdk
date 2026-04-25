"""
Status - All status enums for the governance kernel.

Centralized enum definitions to avoid drift.
"""

from enum import Enum


class KernelStatus(Enum):
    """Terminal decision statuses (matches database schema)."""
    
    # Blocked states
    BLOCKED_SCHEMA = "BLOCKED_SCHEMA"           # Failed schema validation
    BLOCKED_EMERGENCY = "BLOCKED_EMERGENCY"     # Kill switch active
    BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"   # Missing/invalid capability
    BLOCKED_POLICY = "BLOCKED_POLICY"           # Policy rule blocked
    RATE_LIMITED = "RATE_LIMITED"               # Rate limit exceeded
    
    # Approval states
    PENDING_APPROVAL = "PENDING_APPROVAL"       # Waiting for human review
    REJECTED_APPROVAL = "REJECTED_APPROVAL"     # Human rejected
    EXPIRED_APPROVAL = "EXPIRED_APPROVAL"       # Approval window expired
    
    # Success states
    ALLOWED = "ALLOWED"                         # Approved to execute
    EXECUTED = "EXECUTED"                       # Successfully executed
    DRY_RUN = "DRY_RUN"                         # Evaluated but not executed
    
    # Failure states
    FAILED_EXECUTION = "FAILED_EXECUTION"       # Execution error
    FAILED_AUDIT = "FAILED_AUDIT"               # Audit logging failed


class ActorType(Enum):
    """Types of actors in the system."""
    AGENT = "agent"
    WORKFLOW = "workflow"
    SERVICE = "service"
    USER_PROXY = "user_proxy"


class ActorStatus(Enum):
    """Lifecycle status of actors."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class PolicyStatus(Enum):
    """Policy lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ScopeType(Enum):
    """Scope types for policies and kill switches."""
    GLOBAL = "global"
    TENANT = "tenant"
    ACTOR = "actor"
    ACTION = "action"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"


class ApprovalStatus(Enum):
    """Approval queue status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ApprovalPriority(Enum):
    """Approval urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PathType(Enum):
    """Execution path types from RUNTIME.md."""
    FAST = "fast"           # Trusted actor, low risk
    STANDARD = "standard"   # Normal governance flow
    STRUCTURED = "structured"  # Multi-step, needs planning
    HIGH_RISK = "high_risk"  # Irreversible, high stakes
    BYPASS = "bypass"       # Emergency bypass (rare)


class AuditEventType(Enum):
    """Types of audit events."""
    ACTION_RECEIVED = "action_received"
    POLICY_EVALUATED = "policy_evaluated"
    KILL_SWITCH_CHECKED = "kill_switch_checked"
    CAPABILITY_CHECKED = "capability_checked"
    RISK_ASSESSED = "risk_assessed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    DECISION_MADE = "decision_made"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"
    ESCALATION_TRIGGERED = "escalation_triggered"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
