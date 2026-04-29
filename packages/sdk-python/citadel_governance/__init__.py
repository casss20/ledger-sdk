"""Citadel Governance SDK for Python.

AI governance for agent builders — one primitive to control, audit, and approve
every action your agents take.

Recommended import (avoids collision with backend ``citadel`` package):

    import citadel_governance as cg

    cg.configure(
        base_url="https://api.citadelsdk.com",
        api_key="your-api-key",
        actor_id="my-agent",
    )

    result = await cg.execute(
        action="email.send",
        resource="user:123",
        payload={"to": "user@example.com"},
    )

Broader dashboard, identity-management, and policy-management helpers are kept
under ``citadel_governance.compatibility`` for existing callers.

Legacy import (still works, emits a DeprecationWarning):

    import citadel  # deprecated — will be removed in v1.0

Links:
- Documentation: https://citadelsdk.com/docs
- Dashboard: https://dashboard.citadelsdk.com
- PyPI: https://pypi.org/project/citadel-governance/
- Source: https://github.com/casss20/citadel-sdk
"""

from citadel_governance._version import __version__
from citadel_governance.sync import CitadelClient as SyncClient  # noqa: F401
from citadel_governance.exceptions import (
    CitadelError,
    ActionBlocked,
    ApprovalRequired,
    NotFound,
    Conflict,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
)
from citadel_governance.models import (
    CitadelResult,
    CapabilityToken,
    Approval,
)
from citadel_governance.client import CitadelClient
from citadel_governance._module_api import (
    configure,
    execute,
    decide,
    get_action,
    list_approvals,
    get_approval,
    approve,
    reject,
    get_kill_switches,
    verify_audit,
    list_audit_events,
    guard,
    wrap,
)
from citadel_governance import compatibility

__all__ = [
    "__version__",
    "CitadelClient",
    "SyncClient",
    "CitadelResult",
    "CapabilityToken",
    "Approval",
    "CitadelError",
    "ActionBlocked",
    "ApprovalRequired",
    "NotFound",
    "Conflict",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "configure",
    "execute",
    "decide",
    "get_action",
    "list_approvals",
    "get_approval",
    "approve",
    "reject",
    "get_kill_switches",
    "verify_audit",
    "list_audit_events",
    "guard",
    "wrap",
    "compatibility",
]
