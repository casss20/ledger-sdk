# Billing & Quotas

CITADEL provides a commercial-grade entitlement layer that connects your governance policies to real-world business logic.

## Overview

The commercial layer ensures that tenants operate within their subscription limits. It handles three core responsibilities:
1. **Plan Management**: Mapping tenants to subscription-backed plans.
2. **Quota Enforcement**: Hard-blocking requests that exceed plan limits (e.g., 10,000 actions/mo).
3. **Payment Recovery**: Handling `past_due` states gracefully without immediate lockout.
4. **Cost Controls**: Enforcing LLM spend budgets before a request is sent to a model provider.

## Provider-Agnostic Architecture

Citadel's commercial layer is **provider-agnostic**. Stripe is the first concrete adapter, but the core logic knows nothing about Stripe.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Core Runtime (governance, identity)      â”‚
â”‚  â†’ reads TenantEntitlements, UsageSnapshot  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  Commercial Layer (entitlement_service,    â”‚
â”‚  usage_service, events)                     â”‚
â”‚  â†’ depends on CommercialRepository port     â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  Stripe Adapter (adapters/stripe/)           â”‚
â”‚  â†’ translates Stripe events to             â”‚
â”‚    provider-agnostic CommercialEvents        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Key rule:** Core identity and governance code never imports from the Stripe adapter. It only sees the `CommercialRepository` port and provider-agnostic models (`TenantEntitlements`, `UsageSnapshot`, `BillingStatus`).

## Cost-Control Enforcement

Cost-control API calls use the `CostControlService` directly. Legacy commercial
quota middleware is preserved for compatibility code, but it is no longer wired
into the default runtime path because subscription gating is not part of the
active cost-enforcement wedge.

### Status Codes

| Code | Meaning | Action required |
|------|---------|-----------------|
| **200 OK** | Plan is active and under quota. | None. |
| **402 Payment Required** | Subscription is `past_due` or `canceled`. | Tenant must update payment method in the Billing Portal. |
| **429 Too Many Requests** | Monthly usage quota has been exceeded. | Tenant must upgrade their plan or wait for the reset date. |

The middleware is **provider-agnostic**. It uses the `CommercialRepository` port to resolve entitlements. The concrete Stripe adapter satisfies this port at runtime, but the middleware itself knows nothing about Stripe.

## Grace Periods

CITADEL implements a **7-day grace period** for `past_due` accounts.
- If a card fails, the subscription enters `past_due`.
- CITADEL continues to allow API execution during the grace period.
- After 7 days, the status shifts to hard-blocked (402), and all governed actions are blocked until payment is resolved.
- When payment succeeds, the grace period is cleared and status returns to `active`.

## Unified Commercial Identity

Citadel treats the commercial identity (plan, status, limits) as **first-class metadata** attached to every tenant. This metadata is:

- **Queryable**: `request.state.entitlements.plan_code`
- **Enforced**: Middleware blocks requests before they reach the policy engine
- **Auditable**: Every entitlement change is logged in the commercial event log
- **Graceful**: `past_due` tenants get a 7-day grace period before hard lockout

## Atomic Quotas

Usage tracking is enforced at the database layer using atomic increments. This prevents "double-dipping" or missed quota checks during high-concurrency bursts from parallel agent fleets.

```sql
-- Conceptual logic inside the CITADEL Kernel
UPDATE billing_usage
SET count = count + 1
WHERE tenant_id = $1 AND plan_id = $2 AND count < limit;
```

## Cost Controls & Budgets

Citadel can enforce LLM spend controls before a model request is made. This is separate from Stripe subscription quotas:

- **Subscription quotas** answer: "Is this tenant allowed to keep using Citadel this month?"
- **Cost budgets** answer: "Is this specific LLM request allowed before it creates spend?"

Budgets are hierarchical and tenant-scoped:

| Scope | Use case |
|------|----------|
| `tenant` | Company-wide or workspace-wide LLM cap |
| `project` | Product, department, or workload cap |
| `agent` | Per-agent spend guardrail |
| `api_key` | Per-key spend guardrail for delegated integrations |

Reset periods are deterministic: `daily`, `weekly`, or `monthly`.

When a projected request would exceed a matching budget, Citadel returns one of three enforcement actions:

| Action | Meaning |
|--------|---------|
| `block` | Stop the request before provider spend occurs. |
| `require_approval` | Surface the request as needing human approval before spend. |
| `throttle` | Tell the caller to slow or defer the request. |

### Pre-request check

```bash
curl -X POST https://api.citadelsdk.com/v1/billing/cost/check \
  -H "Authorization: Bearer $CITADEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "projected_cost_cents": 42,
    "actor_id": "agent-research-1",
    "project_id": "research",
    "provider": "openai",
    "model": "gpt-4.1"
  }'
```

If the response contains `"allowed": false`, the caller must honor `enforcement_action`.

### Spend recording

After execution, record actual spend for attribution and future checks:

```bash
curl -X POST https://api.citadelsdk.com/v1/billing/cost/spend \
  -H "Authorization: Bearer $CITADEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cost_cents": 39,
    "input_tokens": 1200,
    "output_tokens": 300,
    "actor_id": "agent-research-1",
    "project_id": "research",
    "provider": "openai",
    "model": "gpt-4.1"
  }'
```

Cost spend and enforcement events are append-only commercial records. They do not replace `audit_events` or `governance_audit_log`.

### Manual Top-ups

Citadel supports an enterprise-safe manual top-up flow for tenant-level LLM budgets. A top-up is an admin adjustment to an existing cost budget, not a consumer wallet deposit and not a Stripe checkout flow.

MVP rules:

- Top-ups increase an existing `tenant` budget's `amount_cents`.
- The actor must have the `executive` dashboard role.
- The amount must be positive.
- A reason is required and is stored for audit review.
- Each top-up writes an append-only `cost_budget_adjustments` row.
- The same operation records a `cost.budget_top_up` event in `governance_audit_log` with actor, role, tenant, budget, previous amount, added amount, resulting amount, reason, and timestamp.

The dashboard shows the current budget, current spend, projected budget after top-up, and any failure returned by the API. Agent, project, and API-key top-ups are intentionally deferred until budget ownership and approval workflows are more mature.

Out of scope for the MVP: auto-recharge, invoicing, Stripe checkout, payment collection, and approval routing for large top-ups.

## Trust-Aware Quotas

Trust context may reduce effective limits when the agent is revoked or otherwise restricted, but cost enforcement remains the source of truth. Trust must not raise a tenant above the configured billing or budget limit. The final effective quota is capped by the plan limit and active budget policy.

## Self-Service Dashboard

Tenants can manage their own billing via the **CITADEL Dashboard**:
- **Usage Metrics**: Real-time view of API consumption.
- **Plan Selection**: Upgrade/Downgrade between Free, Pro, and Enterprise tiers.
- **Stripe Portal**: Direct link to manage invoices and payment methods securely.

## Adding Future Providers

To add a new billing provider (e.g., Paddle, Chargebee):

1. Create `citadel/commercial/adapters/<provider>/`
2. Implement `CommercialRepository` port in `<provider>_repository.py`
3. Implement event translator in `translator.py` (maps provider events â†’ `CommercialEvent`)
4. Register the new adapter in `apps/runtime/citadel/api/__init__.py`
5. Add provider-specific routes if needed

Core commercial logic, middleware, and policy evaluation require **zero changes**.

---

*Next: [Multi-Tenant Deployment](../recipes/multi-tenant-deployment.md)*
