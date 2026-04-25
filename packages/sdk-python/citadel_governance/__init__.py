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
    AgentIdentity,
    TrustScore,
    CapabilityToken,
    Approval,
    Agent,
    Policy,
    DashboardStats,
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
    register_agent_identity,
    authenticate_agent,
    get_agent_identity,
    list_agent_identities,
    verify_agent_identity,
    revoke_agent_identity,
    challenge_agent,
    verify_challenge,
    get_trust_score,
    request_capability,
    evaluate_all_trust_scores,
    list_agents,
    get_agent,
    create_agent,
    quarantine_agent,
    update_agent,
    list_policies,
    create_policy,
    update_policy,
    delete_policy,
    get_kill_switches,
    toggle_kill_switch,
    get_stats,
    get_metrics_summary,
    verify_audit,
    list_audit_events,
    guard,
    wrap,
)

__all__ = [
    "__version__",
    "CitadelClient",
    "SyncClient",
    "CitadelResult",
    "AgentIdentity",
    "TrustScore",
    "CapabilityToken",
    "Approval",
    "Agent",
    "Policy",
    "DashboardStats",
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
    "register_agent_identity",
    "authenticate_agent",
    "get_agent_identity",
    "list_agent_identities",
    "verify_agent_identity",
    "revoke_agent_identity",
    "challenge_agent",
    "verify_challenge",
    "get_trust_score",
    "request_capability",
    "evaluate_all_trust_scores",
    "list_agents",
    "get_agent",
    "create_agent",
    "quarantine_agent",
    "update_agent",
    "list_policies",
    "create_policy",
    "update_policy",
    "delete_policy",
    "get_kill_switches",
    "toggle_kill_switch",
    "get_stats",
    "get_metrics_summary",
    "verify_audit",
    "list_audit_events",
    "guard",
    "wrap",
]
