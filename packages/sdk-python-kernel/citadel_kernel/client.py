"""Minimal Citadel Kernel Client - hard cost enforcement + evidence export only."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

# Import CitadelClient from the main SDK
import sys

# Add parent packages to path to import from sdk-python
sdk_python_path = os.path.join(os.path.dirname(__file__), "..", "..", "sdk-python")
if sdk_python_path not in sys.path:
    sys.path.insert(0, sdk_python_path)

from citadel_governance import CitadelClient, CitadelResult


class KernelClient:
    """Minimal Citadel Kernel Client for hard cost enforcement and audit evidence.

    Exposes only:
    - execute() — submit action for governance (pre-execution budget block)
    - decide() — dry-run governance decision without execution
    - export_evidence() — fetch decision evidence bundle with hash verification

    No dashboard, orchestration, or billing surface. Embeddable in agent frameworks.

    Usage:
        client = KernelClient(
            base_url="https://api.citadelsdk.com",
            api_key="sk_xxx",
            actor_id="my-agent",
        )

        result = await client.execute(
            action="llm.generate",
            resource="anthropic:claude",
            provider="anthropic",
            model="claude-opus-4-7",
            input_tokens=10_000,
            output_tokens=2_000,
        )

        if result.status == "executed":
            print("Action allowed, executed by backend")
        elif result.status == "pending_approval":
            print(f"Requires approval: {result.reason}")
        else:
            print(f"Blocked: {result.reason}")

        # Export decision evidence for audit
        evidence = await client.export_evidence(result.action_id)
        print(f"Decision evidence exported with root hash: {evidence['root_hash']}")
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        actor_id: str | None = None,
        actor_type: str = "agent",
        timeout: float = 30.0,
    ):
        """Initialize Kernel Client with Citadel API connection.

        Args:
            base_url: Citadel API base URL (defaults to env CITADEL_URL or localhost:8000)
            api_key: API key for authentication (defaults to env CITADEL_API_KEY)
            actor_id: Agent/actor identifier (defaults to env CITADEL_ACTOR_ID or "default")
            actor_type: Type of actor (default: "agent")
            timeout: HTTP request timeout in seconds (default: 30)
        """
        self._client = CitadelClient(
            base_url=base_url,
            api_key=api_key,
            actor_id=actor_id,
            actor_type=actor_type,
            timeout=timeout,
        )

    async def execute(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] | None = None,
        actor_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        projected_cost_cents: int | None = None,
    ) -> CitadelResult:
        """Execute an action under governance control with pre-execution budget enforcement.

        The Citadel Kernel will:
        1. Estimate cost from provider/model/tokens (or accept explicit projected_cost_cents)
        2. Check all active budgets (tenant, project, agent, api_key scope)
        3. BLOCK before execution if any budget with "block" enforcement would be exceeded
        4. Emit spend_limit_exceeded audit event if blocked
        5. Execute the action if allowed
        6. Return decision (executed, pending_approval, or blocked)

        Args:
            action: Action name (e.g., "llm.generate", "email.send")
            resource: Resource identifier (e.g., "anthropic:claude", "user:123")
            payload: Optional action payload dict
            actor_id: Override default actor_id for this action
            provider: LLM provider (e.g., "anthropic") for cost estimation
            model: Model name (e.g., "claude-opus-4-7") for cost estimation
            input_tokens: Input token count for cost estimation
            output_tokens: Output token count for cost estimation
            projected_cost_cents: Explicit cost in cents (overrides estimation)

        Returns:
            CitadelResult with status (executed, blocked, pending_approval, etc.)
            and reason explaining the decision.
        """
        return await self._client.execute(
            action=action,
            resource=resource,
            payload=payload,
            actor_id=actor_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            projected_cost_cents=projected_cost_cents,
        )

    async def decide(
        self,
        action: str,
        resource: str,
        payload: Dict[str, Any] | None = None,
        actor_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        projected_cost_cents: int | None = None,
    ) -> CitadelResult:
        """Get a governance decision without executing the action (dry-run).

        Same as execute() but evaluates policies and budgets without running the
        action. Useful for checking what would happen without side effects.

        Returns:
            CitadelResult with dry_run status and the decision that would be made.
        """
        return await self._client.decide(
            action=action,
            resource=resource,
            payload=payload,
            actor_id=actor_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            projected_cost_cents=projected_cost_cents,
        )

    async def export_evidence(self, decision_id: str) -> Dict[str, Any]:
        """Export decision evidence bundle with cryptographic verification.

        Returns a JSON bundle containing:
        - decision record (status, winning_rule, reason, timestamps)
        - full audit chain (all events in chronological order)
        - root hash (SHA256 over all events — detects tampering)

        Used for regulatory reporting and audit verification.

        Args:
            decision_id: UUID of the decision to export

        Returns:
            Dict with decision, audit_events, root_hash, and metadata
        """
        response = await self._client._request(
            "GET",
            f"/v1/audit/evidence/{decision_id}",
        )
        from citadel_governance._http import _raise_for_status

        _raise_for_status(response)
        return response.json()

    async def verify_evidence(self, decision_id: str) -> Dict[str, Any]:
        """Verify the tamper-evidence of a decision bundle.

        Recomputes the root hash from all audit events and compares it to the
        stored hash. Returns True if the evidence has not been modified.

        Args:
            decision_id: UUID of the decision to verify

        Returns:
            Dict with verified (bool), root_hash, and event_count
        """
        response = await self._client._request(
            "POST",
            f"/v1/audit/evidence/{decision_id}/verify",
        )
        from citadel_governance._http import _raise_for_status

        _raise_for_status(response)
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self._client.close()

    async def __aenter__(self) -> KernelClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
