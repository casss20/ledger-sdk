# Billing & Quotas

Ledger provides a commercial-grade entitlement layer that connects your governance policies to real-world business logic.

## Overview

The commercial layer ensures that tenants operate within their subscription limits. It handles three core responsibilities:
1. **Plan Management**: Mapping tenants to Stripe-backed subscriptions.
2. **Quota Enforcement**: Hard-blocking requests that exceed plan limits (e.g., 10,000 actions/mo).
3. **Payment Recovery**: Handling `past_due` states gracefully without immediate lockout.

## The Billing Middleware

Every request to the Ledger API passes through a Billing Middleware. This middleware performs an atomic lookup of the tenant's current usage and subscription status.

### Status Codes

| Code | Meaning | Action required |
|------|---------|-----------------|
| **200 OK** | Plan is active and under quota. | None. |
| **402 Payment Required** | Subscription is `past_due` or `canceled`. | Tenant must update payment method in the Billing Portal. |
| **429 Too Many Requests** | Monthly usage quota has been exceeded. | Tenant must upgrade their plan or wait for the reset date. |

## Grace Periods

Ledger implements a **7-day grace period** for `past_due` accounts. 
- If a card fails, the subscription enters `past_due`.
- Ledger continues to allow API execution but flags the response with a warning header.
- After 7 days, the status shifts to `locked` (402), and all governed actions are blocked until payment is resolved.

## Atomic Quotas

Usage tracking is enforced at the database layer using atomic increments. This prevents "double-dipping" or missed quota checks during high-concurrency bursts from parallel agent fleets.

```sql
-- Conceptual logic inside the Ledger Kernel
UPDATE billing_usage 
SET count = count + 1 
WHERE tenant_id = $1 AND plan_id = $2 AND count < limit;
```

## Self-Service Dashboard

Tenants can manage their own billing via the **Ledger Dashboard**:
- **Usage Metrics**: Real-time view of API consumption.
- **Plan Selection**: Upgrade/Downgrade between Free, Pro, and Enterprise tiers.
- **Stripe Portal**: Direct link to manage invoices and payment methods securely.

---

*Next: [Multi-Tenant Deployment](../recipes/multi-tenant-deployment.md)*
