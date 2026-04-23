# REST API Reference

## What you'll learn

- Ledger REST API endpoints
- Authentication and headers
- Request/response formats
- Pagination and filtering
- Rate limiting

---

## Base URL

```
Sandbox:    https://api-sandbox.ledger.dev/v1
Production: https://api.ledger.dev/v1
```

---

## Authentication

All requests require an `Authorization` header:

```
Authorization: Bearer ldk_test_xxxxxxxxxxxxxxxx
```

---

## Core Endpoints

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
