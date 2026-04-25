"""CitadelClient — async HTTP client for the Citadel Governance API."""

import asyncio
import os
import random
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from citadel_governance._http import _raise_for_status
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
    Full-featured HTTP client for the Citadel Governance API.

    Can be used as an async context manager::

        async with CitadelClient(base_url=..., api_key=...) as citadel:
            result = await citadel.execute(action="db.write", resource="users")

    Connection options::

        client = CitadelClient(
            base_url="https://ledger-sdk.fly.dev",
            api_key="sk_xxx",
            timeout=60.0,
            proxies={"https": "http://proxy.example.com:8080"},
            max_retries=3,
        )
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
        event_hooks: Dict[str, List[Callable]] | None = None,
        max_retries: int = 3,
    ):
        _url: str = base_url if base_url is not None else (os.getenv("CITADEL_URL") or "http://localhost:8000")
        self.base_url = _url.rstrip("/")
        self.api_key = api_key or os.getenv("CITADEL_API_KEY", "")
        self.actor_id = actor_id or os.getenv("CITADEL_ACTOR_ID", "default")
        self.actor_type = actor_type
        self.max_retries = max_retries

        client_kwargs: Dict[str, Any] = {
            "base_url": self.base_url,
            "headers": self._default_headers(),
            "timeout": timeout,
        }
        if proxies:
            # httpx proxy accepts str URL or dict {protocol: url}
            if isinstance(proxies, dict):
                # Use the first protocol's URL as the primary proxy
                proxy_url = next(iter(proxies.values()))
                client_kwargs["proxy"] = proxy_url
            else:
                client_kwargs["proxy"] = proxies
        if limits:
            client_kwargs["limits"] = limits
        if event_hooks:
            client_kwargs["event_hooks"] = event_hooks

        self._client = httpx.AsyncClient(**client_kwargs)

    def _default_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Make an authenticated request with retry logic."""
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.NetworkError as exc:
                last_exception = exc
                if attempt == self.max_retries:
                    from citadel_governance.exceptions import CitadelError

                    raise CitadelError(
                        f"Network error after {self.max_retries} retries: {exc}",
                        status=0,
                    ) from exc
                delay = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
                continue

            # Retry on 429 (rate limit) and 5xx (server errors)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.max_retries:
                    _raise_for_status(response)
                    return response  # should never reach; _raise_for_status raises

                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    delay = float(retry_after)
                else:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
                continue

            return response

        # Fallback — should only be reached after network errors exhausted
        from citadel_governance.exceptions import CitadelError

        raise CitadelError(
            f"Request failed after {self.max_retries} retries: {last_exception}"
        )

    # ── Actions ──────────────────────────────────────────────────────────

    async def execute(
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
        """Execute an action under governance control."""
        request: Dict[str, Any] = {
            "actor_id": actor_id or self.actor_id,
            "actor_type": actor_type or self.actor_type,
            "action_name": action,
            "resource": resource,
            "payload": payload or {},
            "context": context or {},
        }
        if idempotency_key:
            request["idempotency_key"] = idempotency_key
        if capability_token:
            request["capability_token"] = capability_token
        if dry_run:
            request["dry_run"] = True

        response = await self._request("POST", "/v1/actions/execute", json=request)
        _raise_for_status(response)
        data = response.json()

        return CitadelResult(
            action_id=data["action_id"],
            status=data["status"],
            winning_rule=data["winning_rule"],
            reason=data["reason"],
            executed=data["executed"],
            result=data.get("result"),
            error=data.get("error"),
        )

    async def decide(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> CitadelResult:
        """
        Get a governance decision without executing the action (dry run).

        Same as :meth:`execute` but sets ``dry_run=True`` so the backend
        evaluates policies and rules without actually running the action.
        """
        return await self.execute(
            action=action,
            resource=resource,
            payload=payload,
            context=context,
            actor_id=actor_id,
            actor_type=actor_type,
            dry_run=True,
        )

    async def get_action(self, action_id: str) -> Dict[str, Any]:
        """Get action details and its decision by ID."""
        response = await self._request("GET", f"/v1/actions/{action_id}")
        _raise_for_status(response)
        return response.json()

    # ── Approvals ──────────────────────────────────────────────────────

    async def list_approvals(
        self, status: str | None = None, limit: int = 100
    ) -> List[Approval]:
        """List approvals, optionally filtered by status."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status_filter"] = status
        response = await self._request("GET", "/v1/approvals", params=params)
        _raise_for_status(response)
        data = response.json()
        return [Approval(**a) for a in data.get("approvals", [])]

    async def get_approval(self, approval_id: str) -> Approval:
        """Get approval details by ID."""
        response = await self._request("GET", f"/v1/approvals/{approval_id}")
        _raise_for_status(response)
        data = response.json()
        return Approval(**data)

    async def approve(
        self, approval_id: str, reviewed_by: str, reason: str = "Approved"
    ) -> Approval:
        """Approve a pending request."""
        response = await self._request(
            "POST",
            f"/v1/approvals/{approval_id}/approve",
            json={"reviewed_by": reviewed_by, "reason": reason},
        )
        _raise_for_status(response)
        data = response.json()
        return Approval(**data)

    async def reject(
        self, approval_id: str, reviewed_by: str, reason: str = "Rejected"
    ) -> Approval:
        """Reject a pending request."""
        response = await self._request(
            "POST",
            f"/v1/approvals/{approval_id}/reject",
            json={"reviewed_by": reviewed_by, "reason": reason},
        )
        _raise_for_status(response)
        data = response.json()
        return Approval(**data)

    # ── Agent Identities ───────────────────────────────────────────────

    async def register_agent_identity(
        self,
        agent_id: str,
        name: str,
        tenant_id: str = "default",
        owner: str | None = None,
    ) -> AgentIdentity:
        """Register a new agent identity. Returns api_key, secret_key, public_key."""
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "name": name,
            "tenant_id": tenant_id,
        }
        if owner:
            payload["owner"] = owner
        response = await self._request("POST", "/api/agent-identities", json=payload)
        _raise_for_status(response)
        data = response.json()
        return AgentIdentity(
            agent_id=data["agent_id"],
            api_key=data["api_key"],
            secret_key=data["secret_key"],
            public_key=data["public_key"],
            trust_score=data.get("trust_score", 0.0),
            trust_level=data.get("trust_level", "unverified"),
        )

    async def authenticate_agent(
        self, agent_id: str, secret_key: str
    ) -> Dict[str, Any]:
        """Authenticate an agent with its secret key."""
        response = await self._request(
            "POST",
            f"/api/agent-identities/{agent_id}/authenticate",
            json={"secret_key": secret_key},
        )
        _raise_for_status(response)
        return response.json()

    async def get_agent_identity(self, agent_id: str) -> Dict[str, Any]:
        """Get agent identity details."""
        response = await self._request("GET", f"/api/agent-identities/{agent_id}")
        _raise_for_status(response)
        return response.json()

    async def list_agent_identities(self) -> List[Dict[str, Any]]:
        """List all agent identities for the tenant."""
        response = await self._request("GET", "/api/agent-identities")
        _raise_for_status(response)
        return response.json().get("identities", [])

    async def verify_agent_identity(self, agent_id: str) -> Dict[str, Any]:
        """Verify an agent identity (cryptographic attestation)."""
        response = await self._request(
            "POST", f"/api/agent-identities/{agent_id}/verify"
        )
        _raise_for_status(response)
        return response.json()

    async def revoke_agent_identity(
        self, agent_id: str, reason: str = "Revoked via SDK"
    ) -> Dict[str, Any]:
        """Revoke an agent identity."""
        response = await self._request(
            "POST",
            f"/api/agent-identities/{agent_id}/revoke",
            json={"reason": reason},
        )
        _raise_for_status(response)
        return response.json()

    async def challenge_agent(self, agent_id: str) -> Dict[str, Any]:
        """Request a challenge for challenge-response authentication."""
        response = await self._request(
            "POST", f"/api/agent-identities/{agent_id}/challenge"
        )
        _raise_for_status(response)
        return response.json()

    async def verify_challenge(
        self, agent_id: str, signature: str
    ) -> Dict[str, Any]:
        """Verify a challenge-response signature."""
        response = await self._request(
            "POST",
            f"/api/agent-identities/{agent_id}/challenge/verify",
            json={"signature": signature},
        )
        _raise_for_status(response)
        return response.json()

    async def get_trust_score(self, agent_id: str) -> TrustScore:
        """Get the current trust score for an agent."""
        response = await self._request(
            "GET", f"/api/agent-identities/{agent_id}/trust"
        )
        _raise_for_status(response)
        data = response.json()
        return TrustScore(
            agent_id=data["agent_id"],
            score=data["score"],
            level=data["level"],
            factors=data.get("factors", {}),
        )

    async def request_capability(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Request a capability token for an action.

        Returns ``{verified, authorized, token, error?}``.
        """
        response = await self._request(
            "POST",
            f"/api/agent-identities/{agent_id}/capability",
            json={"action": action, "resource": resource, "context": context or {}},
        )
        _raise_for_status(response)
        return response.json()

    async def evaluate_all_trust_scores(self) -> List[Dict[str, Any]]:
        """Re-evaluate trust scores for all agents."""
        response = await self._request(
            "POST", "/api/agent-identities/trust/evaluate-all"
        )
        _raise_for_status(response)
        return response.json().get("scores", [])

    # ── Agents (Management) ────────────────────────────────────────────

    async def list_agents(self) -> List[Agent]:
        """List all agents."""
        response = await self._request("GET", "/api/agents")
        _raise_for_status(response)
        data = response.json()
        return [Agent(**a) for a in data.get("agents", [])]

    async def get_agent(self, agent_id: str) -> Agent:
        """Get agent details."""
        response = await self._request("GET", f"/api/agents/{agent_id}")
        _raise_for_status(response)
        return Agent(**response.json())

    async def create_agent(
        self,
        agent_id: str,
        name: str,
        status: str = "healthy",
        health_score: int = 100,
        token_budget: int = 100000,
        owner: str = "op-1",
    ) -> Agent:
        """Create a new agent."""
        response = await self._request(
            "POST",
            "/api/agents",
            json={
                "agent_id": agent_id,
                "name": name,
                "status": status,
                "health_score": health_score,
                "token_budget": token_budget,
                "owner": owner,
            },
        )
        _raise_for_status(response)
        return Agent(**response.json())

    async def quarantine_agent(self, agent_id: str) -> Agent:
        """Toggle quarantine status for an agent."""
        response = await self._request(
            "POST", f"/api/agents/{agent_id}/quarantine"
        )
        _raise_for_status(response)
        return Agent(**response.json())

    async def update_agent(self, agent_id: str, **fields: Any) -> Agent:
        """Update agent fields (health_score, status, actions_today, token_spend)."""
        response = await self._request(
            "PATCH", f"/api/agents/{agent_id}", json=fields
        )
        _raise_for_status(response)
        return Agent(**response.json())

    # ── Policies ───────────────────────────────────────────────────────

    async def list_policies(self) -> List[Policy]:
        """List all governance policies."""
        response = await self._request("GET", "/api/policies")
        _raise_for_status(response)
        data = response.json()
        return [Policy(**p) for p in data.get("policies", [])]

    async def create_policy(
        self,
        name: str,
        description: str = "",
        framework: str = "SOC2",
        severity: str = "medium",
    ) -> Policy:
        """Create a new governance policy."""
        response = await self._request(
            "POST",
            "/api/policies",
            json={
                "name": name,
                "description": description,
                "framework": framework,
                "severity": severity,
            },
        )
        _raise_for_status(response)
        return Policy(**response.json())

    async def update_policy(self, policy_id: str, **fields: Any) -> Policy:
        """Update a policy. Fields: name, description, framework, severity, status."""
        response = await self._request(
            "PATCH", f"/api/policies/{policy_id}", json=fields
        )
        _raise_for_status(response)
        return Policy(**response.json())

    async def delete_policy(self, policy_id: str) -> Dict[str, str]:
        """Delete a policy."""
        response = await self._request("DELETE", f"/api/policies/{policy_id}")
        _raise_for_status(response)
        return response.json()

    # ── Kill Switches ──────────────────────────────────────────────────

    async def get_kill_switches(self) -> Dict[str, bool]:
        """Get current kill switch states."""
        response = await self._request("GET", "/api/dashboard/stats")
        _raise_for_status(response)
        data = response.json()
        return data.get("killswitches", {})

    async def toggle_kill_switch(
        self, switch_name: str, active: bool
    ) -> Dict[str, Any]:
        """Toggle a kill switch on or off."""
        response = await self._request(
            "POST",
            "/api/dashboard/kill-switch",
            json={"switch": switch_name, "active": active},
        )
        _raise_for_status(response)
        return response.json()

    # ── Dashboard / Metrics ────────────────────────────────────────────

    async def get_stats(self) -> DashboardStats:
        """Get dashboard statistics."""
        response = await self._request("GET", "/api/dashboard/stats")
        _raise_for_status(response)
        data = response.json()
        return DashboardStats(
            pending_approvals=data["pending_approvals"],
            active_agents=data["active_agents"],
            risk_level=data["risk_level"],
            kill_switches_active=data["kill_switches_active"],
            killswitches=data["killswitches"],
            recent_events_count=data["recent_events_count"],
            total_actions=data["total_actions"],
            approved_this_month=data["approved_this_month"],
            blocked_this_month=data["blocked_this_month"],
            active_agents_24h=data["active_agents_24h"],
            agent_identities=data["agent_identities"],
        )

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get high-level metrics summary."""
        response = await self._request("GET", "/v1/metrics/summary")
        _raise_for_status(response)
        return response.json()

    # ── Audit ──────────────────────────────────────────────────────────

    async def verify_audit(self) -> Dict[str, Any]:
        """Verify audit chain integrity."""
        response = await self._request("GET", "/v1/audit/verify")
        _raise_for_status(response)
        return response.json()

    async def list_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List audit events."""
        response = await self._request("GET", "/api/audit", params={"limit": limit})
        _raise_for_status(response)
        return response.json().get("events", [])

    # ── Decorators / Lifecycle ─────────────────────────────────────────

    def guard(
        self, action: str | None = None, resource: str | None = None
    ) -> Callable:
        """
        Decorator that wraps an async function with governance.

        Usage::

            @client.guard(action="email.send", resource="user:{user_id}")
            async def send_email(user_id: str, body: str):
                ...
        """

        def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                resolved_action = action or fn.__name__
                resolved_resource = resource or resolved_action
                try:
                    resolved_resource = resolved_resource.format(**kwargs)
                except (KeyError, IndexError):
                    pass

                result = await self.execute(
                    action=resolved_action,
                    resource=resolved_resource,
                    payload={"args": args, "kwargs": kwargs},
                )
                if result.status == "executed":
                    return await fn(*args, **kwargs)
                elif result.status == "pending_approval":
                    raise ApprovalRequired(f"Pending approval: {result.reason}")
                else:
                    raise ActionBlocked(
                        f"Blocked: {result.reason} (rule: {result.winning_rule})"
                    )

            return wrapper

        return decorator

    def wrap(self, fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Wrap an existing async function with governance."""
        return self.guard()(fn)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "CitadelClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
