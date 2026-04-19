"""Ledger SDK — AI governance infrastructure."""

# Core exports (from core/)
from .core import (
    # Constitution
    Constitution,
    ConstitutionalRule,
    ConstitutionViolation,
    RuleType,
    SAFETY_CONSTITUTION,
    TRANSPARENCY_CONSTITUTION,
    PRIVACY_CONSTITUTION,
    DEFAULT_CONSTITUTION,
    # Governor
    Governor,
    EscalationLevel,
    ExecutionLocked,
    get_governor,
    # Executor
    Executor,
    ExecutionMode,
    AutonomyMode,
    executor as executor_decorator,
    # Runtime
    Runtime,
    RuntimeContext,
    RuntimeDecision,
    PathType,
    Layer,
    get_runtime,
)

# Public API (from sdk.py)
from .sdk import Ledger, Denied

# Identity & Agent (from root)
from .identity import (
    AgentIdentity,
    AgentRegistry,
    AgentStatus,
    get_registry,
    register_agent,
    get_agent,
)
from .agent import Agent, create_agent

# Legacy modules
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

# Legacy governor import (for backwards compatibility)
from .governor import Governor as LegacyGovernor, ActionRecord, ActionState, get_governor as get_legacy_governor

# Error handling
from .error_handling import try_governed, catch, Retry, Catch, Default, DeadLetter
from .subgraph import SubgraphExecutor, OutputDefinition, Subgraph, get_subgraph_executor
from .analytics import AnalyticsEngine, BehaviorProfiler, TimeWindow, get_analytics, get_profiler
from .dashboard_api import DashboardAPI, create_dashboard_api, get_fastapi_router

# Governance (submodules)
from .governance.alignment import (
    Alignment,
    ChallengeResult,
    InitiativeLevel,
    Challenge,
    AlignmentCheck,
    get_alignment,
)
from .governance.critic import (
    Critic,
    ReviewResult,
    ReviewDimension,
    get_critic,
)
from .governance.prune import (
    Prune,
    PruneTarget,
    get_prune,
)
from .governance.after_action import (
    AfterAction,
    AfterActionReport,
    get_after_action,
)
from .governance.risk import classify as classify_risk, Approval, Risk
from .governance.killswitch import KillSwitch
from .governance.audit import AuditService
from .governance.rate_limit import RateLimiter, TokenBucket
from .governance.capability import CapabilityIssuer
from .governance.durable import DurablePromise, DurableApprovalQueue, get_durable_queue

# Operations subpackage
from .ops import (
    Planner,
    Plan,
    PlanType,
    PlanningContext,
    get_planner,
    Failure,
    FailureType,
    RecoveryAction,
    FailureContext,
    get_failure,
    Adaptation,
    AdaptationType,
    AdaptationConfig,
    get_adaptation,
    OpportunityDetector,
    Opportunity,
    OpportunityType,
    get_opportunity_detector,
)

# System subpackage
from .system import (
    Focus,
    FocusState,
    CurrentTask,
    get_focus,
)

__all__ = [
    # Core (NEW STRUCTURE)
    # Constitution
    "Constitution",
    "ConstitutionalRule", 
    "ConstitutionViolation",
    "RuleType",
    "SAFETY_CONSTITUTION",
    "TRANSPARENCY_CONSTITUTION",
    "PRIVACY_CONSTITUTION",
    "DEFAULT_CONSTITUTION",
    # Governor
    "Governor",
    "EscalationLevel",
    "ExecutionLocked",
    "get_governor",
    # Executor
    "Executor",
    "ExecutionMode",
    "AutonomyMode",
    "executor_decorator",
    # Runtime
    "Runtime",
    "RuntimeContext",
    "RuntimeDecision",
    "PathType",
    "Layer",
    "get_runtime",
    # Public API
    "Ledger",
    "Denied",
    "Agent",
    "create_agent",
    # Identity
    "AgentIdentity",
    "AgentRegistry", 
    "AgentStatus",
    "get_registry",
    "register_agent",
    "get_agent",
    # Legacy modules
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
    "SidecarClient",
    "PostgresSidecar",
    "RedisSidecar",
    # Legacy governor (backwards compat)
    "LegacyGovernor",
    "ActionRecord",
    "ActionState",
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
    # Alignment
    "Alignment",
    "ChallengeResult",
    "InitiativeLevel",
    "Challenge",
    "AlignmentCheck",
    "get_alignment",
    # Critic (NEW)
    "Critic",
    "ReviewResult", 
    "ReviewDimension",
    "get_critic",
    # Prune (NEW)
    "Prune",
    "PruneTarget",
    "get_prune",
    # After Action (NEW)
    "AfterAction",
    "AfterActionReport",
    "get_after_action",
    # Operations (NEW)
    # Planner
    "Planner",
    "Plan",
    "PlanType",
    "PlanningContext",
    "get_planner",
    # Failure
    "Failure",
    "FailureType",
    "RecoveryAction",
    "FailureContext",
    "get_failure",
    # Adaptation
    "Adaptation",
    "AdaptationType",
    "AdaptationConfig",
    "get_adaptation",
    # Opportunity
    "OpportunityDetector",
    "Opportunity",
    "OpportunityType",
    "get_opportunity_detector",
    # System (NEW)
    # Focus
    "Focus",
    "FocusState",
    "CurrentTask",
    "get_focus",
]
