"""Citadel Kernel — Minimal embeddable governance engine.

Hard cost enforcement + cryptographic decision audit evidence.
No dashboard, orchestration, or billing surface.

Exposes:
- KernelClient: Main client class
- execute(): Module-level function
- decide(): Module-level function
- export_evidence(): Module-level function

All backed by CitadelClient from the main SDK.

Quickstart:
    import citadel_kernel as ck

    client = ck.KernelClient(
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
        print("Cost was within budget, action executed")
    else:
        print(f"Decision: {result.status} — {result.reason}")

    evidence = await client.export_evidence(result.action_id)
    verified = await client.verify_evidence(result.action_id)
    print(f"Evidence verified: {verified['verified']}")
"""

__version__ = "0.1.0"

from citadel_kernel.client import KernelClient

__all__ = [
    "KernelClient",
    "__version__",
]


# Module-level client instance (lazy-initialized on first use)
_default_client = None


def _get_default_client() -> KernelClient:
    """Get or create default client instance from environment variables."""
    global _default_client
    if _default_client is None:
        _default_client = KernelClient()
    return _default_client


async def execute(
    action: str,
    resource: str,
    payload=None,
    actor_id=None,
    provider=None,
    model=None,
    input_tokens=None,
    output_tokens=None,
    projected_cost_cents=None,
):
    """Module-level execute function using default client.

    See KernelClient.execute() for full documentation.
    """
    client = _get_default_client()
    return await client.execute(
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
    action: str,
    resource: str,
    payload=None,
    actor_id=None,
    provider=None,
    model=None,
    input_tokens=None,
    output_tokens=None,
    projected_cost_cents=None,
):
    """Module-level decide function using default client.

    See KernelClient.decide() for full documentation.
    """
    client = _get_default_client()
    return await client.decide(
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


async def export_evidence(decision_id: str):
    """Module-level export_evidence function using default client.

    See KernelClient.export_evidence() for full documentation.
    """
    client = _get_default_client()
    return await client.export_evidence(decision_id)


async def verify_evidence(decision_id: str):
    """Module-level verify_evidence function using default client.

    See KernelClient.verify_evidence() for full documentation.
    """
    client = _get_default_client()
    return await client.verify_evidence(decision_id)
