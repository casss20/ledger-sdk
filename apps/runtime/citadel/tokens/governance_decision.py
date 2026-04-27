"""
Governance Decision — First-class authorization decision.

Why: Every enforcement flow starts with a decision, not a token.
Tokens are optional scoped proofs derived from approved decisions.
Verification resolves the linked decision and checks constraints;
it does NOT create a new decision.
"""

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DecisionType(Enum):
    """Outcome of a governance decision."""

    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    REQUIRE_APPROVAL = "require_approval"
    PENDING = "pending"  # awaiting human approval
    REVOKED = "revoked"


class KillSwitchScope(Enum):
    """Scope at which a kill switch operates."""

    REQUEST = "request"  # single request
    AGENT = "agent"  # all requests from one agent
    TENANT = "tenant"  # all requests from one tenant
    GLOBAL = "global"  # all requests everywhere


@dataclass
class DecisionScope:
    """What a decision permits."""

    actions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    max_spend: Optional[float] = None
    rate_limit: Optional[int] = None

    def covers(self, action: str, resource: Optional[str] = None) -> bool:
        """Check if this scope covers the given action/resource.

        Supports glob patterns in actions and resources (e.g. * or file.*).
        """
        action_matched = False
        for pattern in self.actions:
            if pattern == "*" or fnmatch.fnmatch(action, pattern):
                action_matched = True
                break
        if not action_matched:
            return False
        if resource and self.resources:
            for pattern in self.resources:
                if pattern == "*" or fnmatch.fnmatch(resource, pattern):
                    return True
            return False
        return True


@dataclass
class GovernanceDecision:
    """
    First-class governance decision.

    Central to all enforcement. Tokens are optional derivations.
    Verification resolves this decision and checks:
    - expiry
    - revocation status
    - scope coverage
    - kill-switch state
    """

    decision_id: str  # gd_<uuid>
    decision_type: DecisionType
    tenant_id: str
    actor_id: str  # agent or user who requested
    action: str  # the action being decided
    scope: DecisionScope
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None
    subject_type: str = "agent"
    subject_id: Optional[str] = None
    resource: Optional[str] = None
    risk_level: str = "low"
    policy_version: str = "unknown"
    approval_state: str = "auto_approved"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    constraints: dict = field(default_factory=dict)
    expiry: Optional[datetime] = None
    kill_switch_scope: KillSwitchScope = KillSwitchScope.REQUEST
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    gt_token: Optional[str] = None  # optional derived capability token
    issued_token_id: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    audit_entry_ids: list[str] = field(default_factory=list)
    reason: str = ""
    # Lineage fields for orchestration
    root_decision_id: Optional[str] = None
    parent_decision_id: Optional[str] = None
    parent_actor_id: Optional[str] = None
    workflow_id: Optional[str] = None
    # Trust reproducibility: references the trust snapshot active at decision time
    trust_snapshot_id: Optional[str] = None
    # Authority boundary tracking for handoff
    superseded_at: Optional[datetime] = None
    superseded_reason: Optional[str] = None

    @classmethod
    def generate_id(cls) -> str:
        """Generate a new opaque decision ID (gd_ prefix)."""
        import uuid
        return f"gd_{uuid.uuid4().hex}"

    @property
    def is_expired(self) -> bool:
        if self.expiry is None:
            return False
        return datetime.now(timezone.utc) > self.expiry

    @property
    def is_active(self) -> bool:
        """Decision is active if allowed, not expired, not revoked."""
        return (
            self.decision_type == DecisionType.ALLOW
            and not self.is_expired
            and self.revoked_at is None
        )

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id or self.tenant_id,
            "actor_id": self.actor_id,
            "agent_id": self.agent_id or self.actor_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id or self.actor_id,
            "action": self.action,
            "resource": self.resource,
            "risk_level": self.risk_level,
            "policy_version": self.policy_version,
            "approval_state": self.approval_state,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "scope": {
                "actions": self.scope.actions,
                "resources": self.scope.resources,
                "max_spend": self.scope.max_spend,
                "rate_limit": self.scope.rate_limit,
            },
            "constraints": self.constraints,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "kill_switch_scope": self.kill_switch_scope.value,
            "created_at": self.created_at.isoformat(),
            "gt_token": self.gt_token,
            "issued_token_id": self.issued_token_id or self.gt_token,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "root_decision_id": self.root_decision_id,
            "parent_decision_id": self.parent_decision_id,
            "parent_actor_id": self.parent_actor_id,
            "workflow_id": self.workflow_id,
            "reason": self.reason,
            "superseded_at": self.superseded_at.isoformat() if self.superseded_at else None,
            "superseded_reason": self.superseded_reason,
        }
