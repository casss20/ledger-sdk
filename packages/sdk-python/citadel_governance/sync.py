"""Synchronous wrapper around the async CitadelClient.

Usage::

    from citadel_governance.sync import CitadelClient

    client = CitadelClient(base_url="...", api_key="...")
    result = client.execute(action="email.send", resource="user:123")
    client.close()

    # Or as context manager:
    with CitadelClient(...) as client:
        result = client.execute(action="email.send", resource="user:123")
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

import httpx

from citadel_governance.client import CitadelClient as _AsyncClient
from citadel_governance.exceptions import ActionBlocked, ApprovalRequired
from citadel_governance.models import (
    Agent,
    AgentIdentity,
    Approval,
    CitadelResult,
    DashboardStats,
    Policy,
    TrustScore,
)


class CitadelClient:
    """
    Synchronous HTTP client for the Citadel Governance API.

    Wraps :class:`citadel_governance.client.CitadelClient` and bridges
    every async call with ``asyncio.run()``.

    .. note::
        This client creates an internal event loop. For use in Jupyter
        notebooks or other async contexts, prefer the async client directly.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        actor_id: str | None = None,
        actor_type: str = "agent",
        timeout: float = 30.0,
        proxies: Dict[str, str] | None = None,
        limits: httpx.Limits | None = None,
        max_retries: int = 3,
    ):
        self._async_client = _AsyncClient(
            base_url=base_url,
            api_key=api_key,
            actor_id=actor_id,
            actor_type=actor_type,
            timeout=timeout,
            proxies=proxies,
            limits=limits,
            max_retries=max_retries,
        )

    def _run(self, coro: Any) -> Any:
        """Execute an async coroutine synchronously."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to use asyncio.run
            return asyncio.run(coro)
        # Already inside an async context (e.g. Jupyter) — use the running loop
        return loop.run_until_complete(coro)

    # ── Actions ──────────────────────────────────────────────────────────

    def execute(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
        idempotency_key: str | None = None,
        capability_token: str | None = None,
        dry_run: bool = False,
    ) -> CitadelResult:
        return self._run(
            self._async_client.execute(
                action=action,
                resource=resource,
                payload=payload,
                context=context,
                actor_id=actor_id,
                actor_type=actor_type,
                idempotency_key=idempotency_key,
                capability_token=capability_token,
                dry_run=dry_run,
            )
        )

    def decide(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> CitadelResult:
        return self._run(
            self._async_client.decide(
                action=action,
                resource=resource,
                payload=payload,
                context=context,
                actor_id=actor_id,
                actor_type=actor_type,
            )
        )

    def get_action(self, action_id: str) -> Dict[str, Any]:
        return self._run(self._async_client.get_action(action_id))

    # ── Approvals ──────────────────────────────────────────────────────

    def list_approvals(
        self, status: str | None = None, limit: int = 100
    ) -> List[Approval]:
        return self._run(self._async_client.list_approvals(status=status, limit=limit))

    def get_approval(self, approval_id: str) -> Approval:
        return self._run(self._async_client.get_approval(approval_id))

    def approve(
        self, approval_id: str, reviewed_by: str, reason: str = "Approved"
    ) -> Approval:
        return self._run(
            self._async_client.approve(approval_id, reviewed_by, reason)
        )

    def reject(
        self, approval_id: str, reviewed_by: str, reason: str = "Rejected"
    ) -> Approval:
        return self._run(
            self._async_client.reject(approval_id, reviewed_by, reason)
        )

    # ── Agent Identities ───────────────────────────────────────────────

    def register_agent_identity(
        self,
        agent_id: str,
        name: str,
        tenant_id: str = "default",
        owner: str | None = None,
    ) -> AgentIdentity:
        return self._run(
            self._async_client.register_agent_identity(agent_id, name, tenant_id, owner)
        )

    def authenticate_agent(self, agent_id: str, secret_key: str) -> Dict[str, Any]:
        return self._run(self._async_client.authenticate_agent(agent_id, secret_key))

    def get_agent_identity(self, agent_id: str) -> Dict[str, Any]:
        return self._run(self._async_client.get_agent_identity(agent_id))

    def list_agent_identities(self) -> List[Dict[str, Any]]:
        return self._run(self._async_client.list_agent_identities())

    def verify_agent_identity(self, agent_id: str) -> Dict[str, Any]:
        return self._run(self._async_client.verify_agent_identity(agent_id))

    def revoke_agent_identity(
        self, agent_id: str, reason: str = "Revoked via SDK"
    ) -> Dict[str, Any]:
        return self._run(
            self._async_client.revoke_agent_identity(agent_id, reason)
        )

    def challenge_agent(self, agent_id: str) -> Dict[str, Any]:
        return self._run(self._async_client.challenge_agent(agent_id))

    def verify_challenge(self, agent_id: str, signature: str) -> Dict[str, Any]:
        return self._run(
            self._async_client.verify_challenge(agent_id, signature)
        )

    def get_trust_score(self, agent_id: str) -> TrustScore:
        return self._run(self._async_client.get_trust_score(agent_id))

    def request_capability(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return self._run(
            self._async_client.request_capability(agent_id, action, resource, context)
        )

    def evaluate_all_trust_scores(self) -> List[Dict[str, Any]]:
        return self._run(self._async_client.evaluate_all_trust_scores())

    # ── Agents ────────────────────────────────────────────────────────────

    def list_agents(self) -> List[Agent]:
        return self._run(self._async_client.list_agents())

    def get_agent(self, agent_id: str) -> Agent:
        return self._run(self._async_client.get_agent(agent_id))

    def create_agent(
        self,
        agent_id: str,
        name: str,
        status: str = "healthy",
        health_score: int = 100,
        token_budget: int = 100000,
        owner: str = "op-1",
    ) -> Agent:
        return self._run(
            self._async_client.create_agent(
                agent_id, name, status, health_score, token_budget, owner
            )
        )

    def quarantine_agent(self, agent_id: str) -> Agent:
        return self._run(self._async_client.quarantine_agent(agent_id))

    def update_agent(self, agent_id: str, **fields: Any) -> Agent:
        return self._run(self._async_client.update_agent(agent_id, **fields))

    # ── Policies ───────────────────────────────────────────────────────

    def list_policies(self) -> List[Policy]:
        return self._run(self._async_client.list_policies())

    def create_policy(
        self,
        name: str,
        description: str = "",
        framework: str = "SOC2",
        severity: str = "medium",
    ) -> Policy:
        return self._run(
            self._async_client.create_policy(name, description, framework, severity)
        )

    def update_policy(self, policy_id: str, **fields: Any) -> Policy:
        return self._run(self._async_client.update_policy(policy_id, **fields))

    def delete_policy(self, policy_id: str) -> Dict[str, str]:
        return self._run(self._async_client.delete_policy(policy_id))

    # ── Kill Switches ──────────────────────────────────────────────────

    def get_kill_switches(self) -> Dict[str, bool]:
        return self._run(self._async_client.get_kill_switches())

    def toggle_kill_switch(self, switch_name: str, active: bool) -> Dict[str, Any]:
        return self._run(
            self._async_client.toggle_kill_switch(switch_name, active)
        )

    # ── Dashboard ──────────────────────────────────────────────────────

    def get_stats(self) -> DashboardStats:
        return self._run(self._async_client.get_stats())

    def get_metrics_summary(self) -> Dict[str, Any]:
        return self._run(self._async_client.get_metrics_summary())

    # ── Audit ──────────────────────────────────────────────────────────

    def verify_audit(self) -> Dict[str, Any]:
        return self._run(self._async_client.verify_audit())

    def list_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._run(self._async_client.list_audit_events(limit))

    # ── Decorators ───────────────────────────────────────────────────────

    def guard(
        self, action: str | None = None, resource: str | None = None
    ) -> Callable:
        """
        Synchronous decorator that wraps a function with governance.

        Usage::

            @client.guard(action="email.send", resource="user:{user_id}")
            def send_email(user_id: str, body: str):
                return smtp.send(...)
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                resolved_action = action or fn.__name__
                resolved_resource = resource or resolved_action
                try:
                    resolved_resource = resolved_resource.format(**kwargs)
                except (KeyError, IndexError):
                    pass

                result = self.execute(
                    action=resolved_action,
                    resource=resolved_resource,
                    payload={"args": args, "kwargs": kwargs},
                )
                if result.status == "executed":
                    return fn(*args, **kwargs)
                elif result.status == "pending_approval":
                    raise ApprovalRequired(f"Pending approval: {result.reason}")
                else:
                    raise ActionBlocked(
                        f"Blocked: {result.reason} (rule: {result.winning_rule})"
                    )

            return wrapper

        return decorator

    def wrap(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap an existing function with governance."""
        return self.guard()(fn)

    def close(self) -> None:
        self._run(self._async_client.close())

    def __enter__(self) -> "CitadelClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
