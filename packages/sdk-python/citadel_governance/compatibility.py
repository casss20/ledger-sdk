"""Compatibility-only SDK helpers.

The top-level SDK export is intentionally wedge-focused. This module preserves
broader dashboard, agent-management, policy-management, and identity helpers for
existing callers without presenting them as the primary product surface.
"""

from citadel_governance.models import (
    Agent,
    AgentIdentity,
    DashboardStats,
    Policy,
    TrustScore,
)
from citadel_governance._module_api import (
    authenticate_agent,
    challenge_agent,
    create_agent,
    create_policy,
    delete_policy,
    evaluate_all_trust_scores,
    get_agent,
    get_agent_identity,
    get_metrics_summary,
    get_stats,
    get_trust_score,
    list_agent_identities,
    list_agents,
    list_policies,
    quarantine_agent,
    register_agent_identity,
    request_capability,
    revoke_agent_identity,
    toggle_kill_switch,
    update_agent,
    update_policy,
    verify_agent_identity,
    verify_challenge,
)

__all__ = [
    "Agent",
    "AgentIdentity",
    "DashboardStats",
    "Policy",
    "TrustScore",
    "authenticate_agent",
    "challenge_agent",
    "create_agent",
    "create_policy",
    "delete_policy",
    "evaluate_all_trust_scores",
    "get_agent",
    "get_agent_identity",
    "get_metrics_summary",
    "get_stats",
    "get_trust_score",
    "list_agent_identities",
    "list_agents",
    "list_policies",
    "quarantine_agent",
    "register_agent_identity",
    "request_capability",
    "revoke_agent_identity",
    "toggle_kill_switch",
    "update_agent",
    "update_policy",
    "verify_agent_identity",
    "verify_challenge",
]
