"""Module-level convenience API.

These functions delegate to a lazily-initialized :class:`~citadel_governance.client.CitadelClient`.

Usage::

    import citadel_governance as cg
    cg.configure(base_url="...", api_key="...", actor_id="...")
    result = await cg.execute(action="email.send", resource="user:123")
"""

from typing import Any, Callable, Dict, List, Optional

from citadel_governance.client import CitadelClient
from citadel_governance.models import (
    Agent,
    AgentIdentity,
    Approval,
    CitadelResult,
    DashboardStats,
    Policy,
    TrustScore,
)

_default_client: Optional[CitadelClient] = None


def configure(
    base_url: str | None = None,
    api_key: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "agent",
    timeout: float = 30.0,
    proxies: Dict[str, str] | None = None,
    limits: Any = None,
    event_hooks: Dict[str, List[Callable]] | None = None,
    max_retries: int = 3,
) -> None:
    """Configure the default module-level client."""
    global _default_client
    _default_client = CitadelClient(
        base_url=base_url,
        api_key=api_key,
        actor_id=actor_id,
        actor_type=actor_type,
        timeout=timeout,
        proxies=proxies,
        limits=limits,
        event_hooks=event_hooks,
        max_retries=max_retries,
    )


def _get_client() -> CitadelClient:
    global _default_client
    if _default_client is None:
        configure()
    assert _default_client is not None
    return _default_client


# --- Actions ---
async def execute(*args: Any, **kwargs: Any) -> CitadelResult:
    return await _get_client().execute(*args, **kwargs)


async def decide(*args: Any, **kwargs: Any) -> CitadelResult:
    return await _get_client().decide(*args, **kwargs)


async def get_action(action_id: str) -> Dict[str, Any]:
    return await _get_client().get_action(action_id)


# --- Approvals ---
async def list_approvals(status: str | None = None, limit: int = 100) -> List[Approval]:
    return await _get_client().list_approvals(status=status, limit=limit)


async def get_approval(approval_id: str) -> Approval:
    return await _get_client().get_approval(approval_id)


async def approve(approval_id: str, reviewed_by: str, reason: str = "Approved") -> Approval:
    return await _get_client().approve(approval_id, reviewed_by, reason)


async def reject(approval_id: str, reviewed_by: str, reason: str = "Rejected") -> Approval:
    return await _get_client().reject(approval_id, reviewed_by, reason)


# --- Agent Identities ---
async def register_agent_identity(*args: Any, **kwargs: Any) -> AgentIdentity:
    return await _get_client().register_agent_identity(*args, **kwargs)


async def authenticate_agent(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().authenticate_agent(*args, **kwargs)


async def get_agent_identity(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().get_agent_identity(*args, **kwargs)


async def list_agent_identities() -> List[Dict[str, Any]]:
    return await _get_client().list_agent_identities()


async def verify_agent_identity(agent_id: str) -> Dict[str, Any]:
    return await _get_client().verify_agent_identity(agent_id)


async def revoke_agent_identity(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().revoke_agent_identity(*args, **kwargs)


async def challenge_agent(agent_id: str) -> Dict[str, Any]:
    return await _get_client().challenge_agent(agent_id)


async def verify_challenge(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().verify_challenge(*args, **kwargs)


async def get_trust_score(agent_id: str) -> TrustScore:
    return await _get_client().get_trust_score(agent_id)


async def request_capability(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().request_capability(*args, **kwargs)


async def evaluate_all_trust_scores() -> List[Dict[str, Any]]:
    return await _get_client().evaluate_all_trust_scores()


# --- Agents ---
async def list_agents() -> List[Agent]:
    return await _get_client().list_agents()


async def get_agent(agent_id: str) -> Agent:
    return await _get_client().get_agent(agent_id)


async def create_agent(*args: Any, **kwargs: Any) -> Agent:
    return await _get_client().create_agent(*args, **kwargs)


async def quarantine_agent(agent_id: str) -> Agent:
    return await _get_client().quarantine_agent(agent_id)


async def update_agent(*args: Any, **kwargs: Any) -> Agent:
    return await _get_client().update_agent(*args, **kwargs)


# --- Policies ---
async def list_policies() -> List[Policy]:
    return await _get_client().list_policies()


async def create_policy(*args: Any, **kwargs: Any) -> Policy:
    return await _get_client().create_policy(*args, **kwargs)


async def update_policy(*args: Any, **kwargs: Any) -> Policy:
    return await _get_client().update_policy(*args, **kwargs)


async def delete_policy(*args: Any, **kwargs: Any) -> Dict[str, str]:
    return await _get_client().delete_policy(*args, **kwargs)


# --- Kill Switches ---
async def get_kill_switches() -> Dict[str, bool]:
    return await _get_client().get_kill_switches()


async def toggle_kill_switch(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return await _get_client().toggle_kill_switch(*args, **kwargs)


# --- Dashboard ---
async def get_stats() -> DashboardStats:
    return await _get_client().get_stats()


async def get_metrics_summary() -> Dict[str, Any]:
    return await _get_client().get_metrics_summary()


# --- Audit ---
async def verify_audit() -> Dict[str, Any]:
    return await _get_client().verify_audit()


async def list_audit_events(limit: int = 100) -> List[Dict[str, Any]]:
    return await _get_client().list_audit_events(limit=limit)


# --- Decorators ---
def guard(*args: Any, **kwargs: Any) -> Callable:
    return _get_client().guard(*args, **kwargs)


def wrap(fn: Callable) -> Callable:
    return _get_client().wrap(fn)
