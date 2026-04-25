"""Data models for the Citadel Governance SDK."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CitadelResult:
    """Result of an action through Citadel governance."""

    action_id: str
    status: str  # executed | blocked | pending_approval | failed_execution
    winning_rule: str
    reason: str
    executed: bool
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AgentIdentity:
    """Agent identity registration result."""

    agent_id: str
    api_key: str
    secret_key: str
    public_key: str
    trust_score: float
    trust_level: str


@dataclass
class TrustScore:
    """Agent trust score."""

    agent_id: str
    score: float
    level: str
    factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityToken:
    """Time-bound capability token."""

    type: str
    agent_id: str
    action: str
    resource: str
    issued_at: str
    expires_at: str
    trust_level: str


@dataclass
class Approval:
    """Approval request."""

    id: str
    action: str
    status: str = "pending"
    priority: str = "medium"
    reason: str = ""
    requested_by: str = ""
    reviewed_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_reason: Optional[str] = None


@dataclass
class Agent:
    """Agent record."""

    agent_id: str
    name: str = ""
    status: str = "healthy"
    health_score: int = 100
    token_spend: int = 0
    token_budget: int = 100000
    actions_today: int = 0
    owner: str = "op-1"
    quarantined: bool = False
    compliance: List[str] = field(default_factory=list)
    tenant_id: str = "default"
    created_at: Optional[str] = None


@dataclass
class Policy:
    """Governance policy."""

    id: str
    name: str = ""
    description: str = ""
    framework: str = "SOC2"
    severity: str = "medium"
    status: str = "active"
    tenant_id: str = "default"
    created_at: Optional[str] = None


@dataclass
class DashboardStats:
    """Dashboard statistics."""

    pending_approvals: int
    active_agents: int
    risk_level: str
    kill_switches_active: int
    killswitches: Dict[str, bool]
    recent_events_count: int
    total_actions: int
    approved_this_month: int
    blocked_this_month: int
    active_agents_24h: int
    agent_identities: Dict[str, Any]
