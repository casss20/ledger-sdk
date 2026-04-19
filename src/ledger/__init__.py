"""Ledger SDK — AI governance infrastructure."""

from .sdk import Ledger, Denied
from .loader import build_system_prompt
from .classifier import classify
from .schema import AgentOutput, OutputType, ApprovalLevel
from .router import LedgerRouter, RoutingDecision

# Weft-inspired patterns
from .mocking import mockable, MockRegistry, Mock
from .validation import validate_at_startup, GovernanceConfig, Validator
from .dense import gov, DenseRule
from .null_propagation import Required, Optional, SkipExecution
from .groups import ActionGroup, ActionNode, get_registry
from .sidecar import SidecarClient, PostgresSidecar, RedisSidecar
from .governor import Governor, ActionRecord, ActionState, get_governor
from .error_handling import try_governed, catch, Retry, Catch, Default, DeadLetter
from .subgraph import SubgraphExecutor, OutputDefinition, Subgraph, get_subgraph_executor
from .analytics import AnalyticsEngine, BehaviorProfiler, TimeWindow, get_analytics, get_profiler
from .dashboard_api import DashboardAPI, create_dashboard_api, get_fastapi_router

# Identity, Constitution, Agent (new core files)
from .constitution import (
    Constitution,
    ConstitutionalRule,
    ConstitutionViolation,
    RuleType,
    SAFETY_CONSTITUTION,
    TRANSPARENCY_CONSTITUTION,
    PRIVACY_CONSTITUTION,
    DEFAULT_CONSTITUTION,
)
from .identity import (
    AgentIdentity,
    AgentRegistry,
    AgentStatus,
    get_registry,
    register_agent,
    get_agent,
)
from .agent import Agent, create_agent

# Governance subpackage
from .governance.alignment import (
    Alignment,
    ChallengeResult,
    InitiativeLevel,
    Challenge,
    AlignmentCheck,
    get_alignment,
)
from .governance.risk import classify as classify_risk, Approval, Risk
from .governance.killswitch import KillSwitch
from .governance.audit import AuditService
from .governance.rate_limit import RateLimiter, TokenBucket
from .governance.capability import CapabilityIssuer
from .governance.durable import DurablePromise, DurableApprovalQueue, get_durable_queue

__all__ = [
    # Core
    "Ledger",
    "Denied",
    "Agent",
    "create_agent",
    # Identity & Constitution
    "AgentIdentity",
    "AgentRegistry", 
    "AgentStatus",
    "Constitution",
    "ConstitutionalRule",
    "ConstitutionViolation",
    "RuleType",
    "SAFETY_CONSTITUTION",
    "TRANSPARENCY_CONSTITUTION", 
    "PRIVACY_CONSTITUTION",
    "DEFAULT_CONSTITUTION",
    "get_registry",
    "register_agent",
    "get_agent",
    "build_system_prompt",
    "classify",
    "AgentOutput",
    "OutputType",
    "ApprovalLevel",
    "LedgerRouter",
    "RoutingDecision",
    # Weft patterns
    "mockable",
    "MockRegistry",
    "Mock",
    "validate_at_startup",
    "GovernanceConfig",
    "Validator",
    "gov",
    "DenseRule",
    "Required",
    "Optional",
    "SkipExecution",
    "ActionGroup",
    "ActionNode",
    "get_registry",
    "SidecarClient",
    "PostgresSidecar",
    "RedisSidecar",
    # Governor
    "Governor",
    "ActionRecord",
    "ActionState",
    "get_governor",
    # Error handling
    "try_governed",
    "catch",
    "Retry",
    "Catch",
    "Default",
    "DeadLetter",
    # Subgraph execution
    "SubgraphExecutor",
    "OutputDefinition",
    "Subgraph",
    "get_subgraph_executor",
    # Analytics
    "AnalyticsEngine",
    "BehaviorProfiler",
    "TimeWindow",
    "get_analytics",
    "get_profiler",
    # Dashboard API
    "DashboardAPI",
    "create_dashboard_api",
    "get_fastapi_router",
    # Governance (submodules)
    "classify_risk",
    "Approval",
    "Risk",
    "KillSwitch",
    "AuditService",
    "RateLimiter",
    "TokenBucket",
    "CapabilityIssuer",
    "DurablePromise",
    "DurableApprovalQueue",
    "get_durable_queue",
]
