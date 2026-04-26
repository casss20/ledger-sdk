"""Backward-compatible shim for legacy ``import citadel``.

.. deprecated::
    This import path is deprecated and will be removed in v1.0.
    Please use ``import citadel_governance as cg`` instead.
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("always", DeprecationWarning)
    warnings.warn(
        "'import citadel' is deprecated. Use 'import citadel_governance as cg' instead. "
        "The 'citadel' module name will be removed in v1.0.",
        DeprecationWarning,
        stacklevel=2,
    )

# Re-export everything from the canonical package
from citadel_governance._version import __version__  # noqa: F401
from citadel_governance.exceptions import *  # noqa: F401,F403
from citadel_governance.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
)
from citadel_governance.models import *  # noqa: F401,F403
from citadel_governance.client import CitadelClient  # noqa: F401
from citadel_governance._module_api import *  # noqa: F401,F403

# Build __all__ robustly from the canonical package instead of
# relying on the fragile ``from citadel_governance import __all__`` pattern.
import citadel_governance as _cg

__all__ = getattr(_cg, "__all__", [
    "__version__",
    "CitadelClient",
    "CitadelResult",
    "ActionBlocked",
    "ApprovalRequired",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "Agent",
    "AgentIdentity",
    "Approval",
    "DashboardStats",
    "NotFound",
    "Policy",
    "TrustScore",
    "Conflict",
    "configure",
    "execute",
    "decide",
    "approve",
    "reject",
    "guard",
    "wrap",
    "verify_audit",
    "get_action",
    "get_agent",
    "get_kill_switches",
    "get_metrics_summary",
    "get_stats",
    "get_trust_score",
    "list_agent_identities",
    "list_agents",
    "list_approvals",
    "list_audit_events",
    "list_policies",
    "create_agent",
    "create_policy",
    "update_agent",
    "update_policy",
    "delete_policy",
    "quarantine_agent",
    "request_capability",
    "revoke_agent_identity",
    "toggle_kill_switch",
])
