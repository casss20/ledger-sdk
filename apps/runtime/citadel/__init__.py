"""Citadel SDK - AI governance infrastructure."""

# ── Public API ──────────────────────────────────────────────────────────
# Keep the runtime package surface minimal to avoid circular imports
# and clearly separate public API from internal implementation details.

# SDK-like convenience surface (from the embedded thin client)
from .core.sdk import (
    CitadelClient,
    CitadelResult,
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

# Core domain types
from .actions import Action, Decision, KernelStatus, KernelResult

# Backward compatibility aliases
Citadel = CitadelClient
Denied = ActionBlocked

__all__ = [
    # SDK surface
    "CitadelClient",
    "Citadel",
    "CitadelResult",
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
    # Core domain
    "Action",
    "Decision",
    "KernelStatus",
    "KernelResult",
]
