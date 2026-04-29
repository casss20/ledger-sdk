# Citadel Kernel — Minimal Governance for AI Agents

**Hard cost enforcement + cryptographic decision audit evidence.**

A lightweight, embeddable governance kernel for agent frameworks. Zero dashboard, orchestration, or billing baggage. Just two wedges:

1. **Pre-execution cost blocking** — estimate LLM cost, check budgets, BLOCK before the API call if exceeded
2. **Cryptographic audit evidence** — export decision bundles with tamper-evident hash chains for regulatory review

## Installation

```bash
pip install citadel-kernel
```

## Quickstart

```python
import citadel_kernel as ck
import asyncio

async def main():
    # Create a kernel client
    client = ck.KernelClient(
        base_url="https://api.citadelsdk.com",
        api_key="sk_your_key_here",
        actor_id="my-agent",
    )

    # Execute an action with cost info
    # Kernel will estimate cost from provider+model+tokens
    result = await client.execute(
        action="llm.generate",
        resource="anthropic:claude",
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=10_000,
        output_tokens=2_000,
    )

    if result.status == "executed":
        print("✓ Cost was within budget, action executed")
    elif result.status == "pending_approval":
        print(f"⏸ Approval required: {result.reason}")
    else:
        print(f"✗ Blocked: {result.reason}")

    # Export decision evidence for audit/compliance
    evidence = await client.export_evidence(result.action_id)
    print(f"Decision evidence exported (hash: {evidence['root_hash'][:16]}...)")

    # Verify the evidence hasn't been tampered with
    verified = await client.verify_evidence(result.action_id)
    print(f"Evidence verified: {verified['verified']}")

    await client.close()

asyncio.run(main())
```

## Cost Estimation

The kernel automatically estimates cost from provider + model + token counts:

```python
# Kernel estimates cost from Anthropic pricing tables
result = await client.execute(
    action="llm.generate",
    resource="anthropic:claude",
    provider="anthropic",
    model="claude-opus-4-7",
    input_tokens=10_000,
    output_tokens=2_000,
)
```

Or provide explicit cost in cents:

```python
result = await client.execute(
    action="llm.generate",
    resource="anthropic:claude",
    projected_cost_cents=1000,  # $10.00
)
```

## Budget Enforcement

Configure budgets via the Citadel dashboard. The kernel checks against:

- **Tenant budgets** — entire organization spending limits
- **Project budgets** — per-project caps
- **Agent budgets** — per-agent caps
- **API key budgets** — per-key caps

If any budget with `block` enforcement would be exceeded, the kernel returns `spend_limit_exceeded` **before** the LLM call is made.

## Audit Evidence

Export decision evidence for regulatory review:

```python
evidence = await client.export_evidence(decision_id)

# Returns:
{
  "decision_id": "dec-abc123",
  "action_id": "act-xyz789",
  "status": "executed",
  "winning_rule": "policy_allow",
  "reason": "Budget check passed",
  "created_at": "2026-04-29T12:34:56Z",
  "policy_snapshot_id": "snap-def456",
  "audit_events": [
    {
      "event_id": 1,
      "event_type": "action_received",
      "actor_id": null,
      "payload": {...},
      "event_ts": "2026-04-29T12:34:56Z"
    },
    ...
  ],
  "root_hash": "a7f3b2c9d1e4..."  # SHA256 over all events
}
```

Verify the evidence hasn't been tampered with:

```python
verified = await client.verify_evidence(decision_id)
# Returns: {"decision_id": "...", "verified": true, "root_hash": "...", "event_count": 5}
```

## Module-Level API

Use the default client without instantiating:

```python
import citadel_kernel as ck

result = await ck.execute(
    action="llm.generate",
    resource="anthropic:claude",
    provider="anthropic",
    model="claude-opus-4-7",
    input_tokens=10_000,
    output_tokens=2_000,
)

evidence = await ck.export_evidence(result.action_id)
```

The default client uses environment variables:
- `CITADEL_URL` — API base URL (defaults to `http://localhost:8000`)
- `CITADEL_API_KEY` — API key for authentication
- `CITADEL_ACTOR_ID` — Actor identifier (defaults to `"default"`)

## What's NOT Included

This kernel does **not** include:

- Dashboard UI (no web interface)
- Orchestration runtime (no multi-step workflows)
- Billing adapters (no Stripe integration)
- Telemetry (no OpenTelemetry)
- Advanced trust scoring (no agent reputation system)
- Multi-tenant management UI

Use the full **[Citadel SDK](https://github.com/casss20/citadel-sdk)** if you need those features.

## Environment Variables

```bash
CITADEL_URL=https://api.citadelsdk.com
CITADEL_API_KEY=sk_your_key_here
CITADEL_ACTOR_ID=my-agent
```

## Documentation

- **Quickstart:** https://citadelsdk.com/docs
- **Cost Estimation:** https://citadelsdk.com/docs/cost-estimation
- **Audit Evidence:** https://citadelsdk.com/docs/audit-evidence
- **Budget Configuration:** https://citadelsdk.com/docs/budgets

## License

**citadel-kernel is Apache License 2.0** — fully open source.

The SDK depends on `citadel-governance` (also Apache 2.0). If you self-host the Citadel runtime backend (`apps/runtime/`), that code is **Business Source License 1.1** (self-host and modify freely, but no competing hosted service without a license agreement).
