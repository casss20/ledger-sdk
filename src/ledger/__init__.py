"""Ledger SDK — AI governance infrastructure."""

# Public API (from sdk.py)
from .sdk import (
    LedgerClient,
    LedgerResult,
    ActionBlocked,
    ApprovalRequired,
    configure,
    execute,
    decide,
    approve,
    reject,
    guard,
    wrap,
    verify_audit,
)

# Backward compatibility aliases
Ledger = LedgerClient
Denied = ActionBlocked

# Core governance engine
from .actions import Action, Decision, KernelStatus, KernelResult
from .execution import Kernel, Executor
from .orchestrator import Orchestrator
from .repository import Repository
from .config import settings

# Services (for advanced use / dependency injection)
from .policy_resolver import PolicyResolver, PolicyEvaluator
from .precedence import Precedence
from .approval_service import ApprovalService
from .audit_service import AuditService
from .capability_service import CapabilityService

__all__ = [
    # SDK
    "LedgerClient",
    "Ledger",
    "LedgerResult",
    "ActionBlocked",
    "Denied",
    "ApprovalRequired",
    "configure",
    "execute",
    "decide",
    "approve",
    "reject",
    "guard",
    "wrap",
    "verify_audit",
    # Core engine
    "Kernel",
    "Action",
    "KernelStatus",
    "KernelResult",
    "Orchestrator",
    "Repository",
    "settings",
    # Services
    "PolicyResolver",
    "PolicyEvaluator",
    "Precedence",
    "ApprovalService",
    "AuditService",
    "CapabilityService",
    "Executor",
]
