# REST API Reference

## What you'll learn

- Citadel REST API endpoints
- Authentication and headers
- Request/response formats
- Pagination and filtering
- Rate limiting

---

## Base URL

```
Sandbox:    https://api-sandbox.citadel.dev/v1
Production: https://api.citadel.dev/v1
```

---

## Authentication

All requests require an `Authorization` header:

```
Authorization: Bearer ldk_test_xxxxxxxxxxxxxxxx
```

---

## Core Endpoints

### Introspect a runtime capability token

High-risk runtimes and tool gateways should call introspection immediately before executing the protected operation. The token is execution proof only; the linked governance decision remains the source of truth.

```http
POST /v1/introspect
Authorization: Bearer <api-key-or-runtime-gateway-credential>
X-Tenant-ID: ws_prod_01
Content-Type: application/json

{
  "token": "gt_cap_abc123",
  "required_action": "stripe.refund.create",
  "required_resource": "customer:2841",
  "workspace_id": "ws_prod_01",
  "tool": "stripe"
}
```

`POST /v1/governance/introspect` is also supported for governance-namespaced clients.

**Active response:**
```json
{
  "active": true,
  "decision_id": "gd_01h...",
  "subject": "agent:payments-01",
  "workspace_id": "ws_prod_01",
  "tool": "stripe",
  "action": "stripe.refund.create",
  "resource_scope": "customer:2841",
  "risk_level": "critical",
  "policy_version": "policy_2026_04_24_7",
  "approval_state": "approved",
  "exp": 1777086372,
  "kill_switch": false,
  "reason": null
}
```

**Inactive response:**
```json
{
  "active": false,
  "decision_id": "gd_01h...",
  "reason": "kill_switch_active",
  "kill_switch": true
}
```

Introspection returns `active: false` when the token is missing, expired, revoked, not yet valid, linked to a revoked decision, outside the requested workspace/action/resource scope, or blocked by a matching kill switch. Runtimes must block execution when `active` is false.

Common inactive reasons include:

| Reason | Meaning |
|--------|---------|
| `token_not_found` | The supplied token does not exist for the tenant. |
| `token_expired` | The `gt_cap_` token lifetime has elapsed. |
| `token_revoked` | The token was centrally revoked. |
| `decision_revoked` | The underlying governance decision is no longer executable. |
| `workspace_mismatch` | The token/decision is not valid for the requested workspace. |
| `scope_mismatch` | The requested action or resource is outside token scope. |
| `kill_switch_active` | Central emergency state blocks the next protected operation. |

### Create a governance decision

Create the durable decision record before issuing a `gt_cap_` token.

```http
POST /v1/governance/decisions
Authorization: Bearer <api-key>
X-Tenant-ID: ws_prod_01
Content-Type: application/json

{
  "request_id": "req_123",
  "trace_id": "trace_123",
  "workspace_id": "ws_prod_01",
  "actor_id": "agent:payments-01",
  "agent_id": "agent:payments-01",
  "subject_type": "agent",
  "subject_id": "agent:payments-01",
  "action": "stripe.refund.create",
  "resource": "customer:2841",
  "risk_level": "critical",
  "policy_version": "policy_2026_04_24_7",
  "approval_state": "approved",
  "approved_by": "operator:admin",
  "scope_actions": ["stripe.refund.create"],
  "scope_resources": ["customer:2841"],
  "constraints": {"tool": "stripe"},
  "decision_type": "allow",
  "reason": "Approved high-risk refund"
}
```

### Issue a short-lived capability token

```http
POST /v1/governance/decisions/{decision_id}/tokens
Authorization: Bearer <api-key>
X-Tenant-ID: ws_prod_01
```

Only `allow` decisions can issue runtime capability tokens. Each active `gt_cap_` token maps to one `decision_id`, and the decision records `issued_token_id` for audit joins.

**Response:**
```json
{
  "token_id": "gt_cap_abc123",
  "decision_id": "gd_01h...",
  "iss": "citadel",
  "subject": "agent:payments-01",
  "audience": "citadel-runtime",
  "workspace_id": "ws_prod_01",
  "tool": "stripe",
  "action": "stripe.refund.create",
  "resource_scope": "customer:2841",
  "risk_level": "critical",
  "expiry": "2026-04-25T12:02:00Z",
  "trace_id": "trace_123"
}
```

### Govern an action

```http
POST /v1/govern
Content-Type: application/json

{
  "agent_id": "agent-123",
  "action": "email.send",
  "params": {
    "to": "user@example.com",
    "subject": "Welcome"
  }
}
```

**Response:**
```json
{
  "governance_token": "gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh",
  "decision": "allowed",
  "policy_name": "email-allowed",
  "timestamp": "2026-04-23T10:30:00Z"
}
```

### Query audit trail

```http
GET /v1/audit?agent_id=agent-123&start=2026-04-01&end=2026-04-30&limit=100
```

**Response:**
```json
{
  "records": [
    {
      "governance_token": "gt_...",
      "agent_id": "agent-123",
      "action": "email.send",
      "decision": "allowed",
      "timestamp": "2026-04-23T10:30:00Z"
    }
  ],
  "total": 42,
  "next_cursor": "eyJpZCI6MTIzfQ=="
}
```

### Activate kill switch

```http
POST /v1/kill-switch/activate
Content-Type: application/json

{
  "scope": "agent",
  "target": "agent-123",
  "reason": "Suspicious activity",
  "duration": "1h"
}
```

### Create policy

```http
POST /v1/policies
Content-Type: application/json

{
  "name": "refund-approval",
  "namespace": "payments",
  "trigger": {
    "action": "refund.create",
    "condition": "amount > 1000"
  },
  "enforcement": {
    "type": "require_approval",
    "approvers": ["finance-manager"]
  }
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden (policy denied) |
| 409 | Conflict |
| 429 | Rate Limited |
| 500 | Server Error |

---

## Pagination

All list endpoints support cursor-based pagination:

```http
GET /v1/audit?limit=100&cursor=eyJpZCI6MTIzfQ==
```

---

## Idempotency

Pass an `Idempotency-Key` header for safe retries:

```http
POST /v1/govern
Idempotency-Key: req-uuid-123
```

---

## Next steps

- [Python SDK Reference](python-sdk.md)
- [TypeScript SDK Reference](typescript-sdk.md)
- [Go SDK Reference](go-sdk.md)
