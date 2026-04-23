"""Ledger Governance Token System — Decision-centric architecture."""

from .governance_decision import (
    GovernanceDecision,
    DecisionScope,
    DecisionType,
    KillSwitchScope,
)
from .governance_token import CapabilityToken
from .decision_engine import DecisionEngine
from .kill_switch import KillSwitch, KillSwitchRecord, KillSwitchCheck
from .token_verifier import TokenVerifier, VerificationResult
from .execution_middleware import ExecutionMiddleware
from .token_vault import TokenVault
from .audit_trail import GovernanceAuditTrail

__all__ = [
    # First-class decision
    "GovernanceDecision",
    "DecisionScope",
    "DecisionType",
    # Kill switch
    "KillSwitch",
    "KillSwitchScope",
    "KillSwitchRecord",
    "KillSwitchCheck",
    # Token (derived from decision)
    "CapabilityToken",
    # Engine
    "DecisionEngine",
    # Verification
    "TokenVerifier",
    "VerificationResult",
    # Middleware
    "ExecutionMiddleware",
    # Vault
    "TokenVault",
    # Audit trail (separated)
    "GovernanceAuditTrail",
]
