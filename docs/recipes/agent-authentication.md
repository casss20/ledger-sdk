# Agent Authentication — Real API Examples

**Document ID:** REC-AGENT-AUTH-001  
**Version:** 1.0  
**Date:** 2026-04-26  

---

## Overview

This replaces the legacy `CITADEL.agents.authenticate()` fantasy API with real HTTP endpoints. All examples use `curl` against the Citadel FastAPI surface.

**Base URL:** `https://api.citadelsdk.com/api` (or `http://localhost:8000/api` for local)

---

## 1. Register a New Agent Identity

Every agent needs a cryptographic identity before it can authenticate or request capabilities.

```bash
curl -X POST http://localhost:8000/api/agent-identities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{
    "agent_id": "agent-scraper-001",
    "name": "Web Scraper Alpha",
    "tenant_id": "demo-tenant",
    "owner": "op-anthony"
  }'
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "secret_key": "ak_lR9vKx...mN3pQ",  // ⚠️ STORE THIS ONCE — never shown again
  "public_key": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA...\n-----END PUBLIC KEY-----",
  "api_key": "ak_demo_7f8a9b2c3d4e5f6"
}
```

**Important:** The `secret_key` is returned **once** at registration. The server stores only its bcrypt hash. If you lose it, you must rotate credentials.

---

## 2. Authenticate with Secret Key

After registration, authenticate to verify the agent exists and get identity metadata.

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "secret_key": "ak_lR9vKx...mN3pQ"
  }'
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "authenticated": true,
  "tenant_id": "demo-tenant",
  "trust_level": "unverified",
  "verification_status": "pending"
}
```

**Response (401):**
```json
{"detail": "Invalid agent_id or secret_key"}
```

---

## 3. Generate an Authentication Challenge

For challenge-response authentication (stronger than secret-key alone):

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/challenge \
  -H "Content-Type: application/json"
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "challenge": "a1b2c3d4e5f6...",  // 64-char hex nonce
  "expires_in": 300                 // 5 minutes
}
```

---

## 4. Verify Challenge Response

The agent signs the challenge with its **private key** (the complement of the `public_key` from registration). Send the signature back:

```bash
# Agent-side (Python example):
# from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
# signature = private_key.sign(challenge.encode()).hex()

curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/challenge/verify \
  -H "Content-Type: application/json" \
  -d '{
    "response": "3f4e5d6c7b8a9012..."  // hex signature
  }'
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "verified": true
}
```

**If challenge expired or signature invalid:**
```json
{"agent_id": "agent-scraper-001", "verified": false}
```

---

## 5. Verify an Agent (Operator Action)

A human operator verifies an agent, elevating its trust level.

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/verify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{
    "verifier_id": "op-anthony"
  }'
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "verified": true,
  "trust_level": "standard"
}
```

After verification, the agent's trust level moves from `unverified` → `standard`.

---

## 6. Get Trust Score

```bash
curl http://localhost:8000/api/agent-identities/agent-scraper-001/trust \
  -H "Authorization: Bearer $API_KEY"
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "score": 0.72,
  "level": "trusted",
  "factors": {
    "verification": 0.25,
    "age": 0.10,
    "health": 0.20,
    "quarantine": 0.10,
    "action_rate": 0.10,
    "compliance": 0.15,
    "budget": 0.05
  }
}
```

**Score breakdown:**
- `verification`: 0.25 (verified by operator)
- `age`: 0.10 (account age > 7 days)
- `health`: 0.20 (health score = 100)
- `quarantine`: 0.10 (not quarantined)
- `action_rate`: 0.10 (normal action volume)
- `compliance`: 0.15 (no recent violations)
- `budget`: 0.05 (spending within budget)

**Total = 0.72 → `trusted` level**

---

## 7. Recalculate Trust Score

Force a fresh trust score calculation:

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/trust/update \
  -H "Authorization: Bearer $ADMIN_JWT"
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "score": 0.75,
  "level": "trusted",
  "factors": { ... }
}
```

---

## 8. Issue a Capability Token

After authentication + verification, request a capability token for a specific action:

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/capability \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "action": "scrape",
    "resource": "https://example.com/data",
    "context": {"rate_limit": 100, "depth": 2}
  }'
```

**Response (200) — Authorized:**
```json
{
  "verified": true,
  "authorized": true,
  "agent_id": "agent-scraper-001",
  "trust_band": "TRUSTED",
  "trust_score": 0.72,
  "trust_snapshot_id": "snap_550e8400-e29b-41d4-a716-446655440000",
  "token": {
    "type": "capability_token",
    "agent_id": "agent-scraper-001",
    "action": "scrape",
    "resource": "https://example.com/data",
    "issued_at": "2026-04-26T01:30:00",
    "expires_at": "2026-04-26T02:30:00",
    "trust_band": "TRUSTED"
  }
}
```

**Response (200) — Denied (trust too low):**
```json
{
  "verified": true,
  "authorized": false,
  "agent_id": "agent-scraper-001",
  "error": "Trust band PROBATION below minimum STANDARD for this action",
  "trust_band": "PROBATION",
  "trust_score": 0.28,
  "trust_snapshot_id": "snap_550e8400-e29b-41d4-a716-446655440000",
  "token": null
}
```

---

## 9. Revoke an Agent Identity

If an agent is compromised or no longer needed:

```bash
curl -X POST http://localhost:8000/api/agent-identities/agent-scraper-001/revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{
    "reason": "Credential leak detected in log stream"
  }'
```

**Response (200):**
```json
{
  "agent_id": "agent-scraper-001",
  "revoked": true,
  "reason": "Credential leak detected in log stream"
}
```

After revocation:
- Agent is immediately blocked from all actions
- All capability tokens are invalidated
- `trust_level` becomes `revoked`
- Audit log entry created

---

## 10. List All Identities

```bash
# All identities (admin only)
curl http://localhost:8000/api/agent-identities \
  -H "Authorization: Bearer $ADMIN_JWT"

# Filtered by tenant
curl "http://localhost:8000/api/agent-identities?tenant_id=demo-tenant" \
  -H "Authorization: Bearer $ADMIN_JWT"
```

**Response (200):**
```json
{
  "identities": [
    {
      "agent_id": "agent-scraper-001",
      "tenant_id": "demo-tenant",
      "public_key": "-----BEGIN PUBLIC KEY-----...",
      "trust_level": "standard",
      "verification_status": "verified",
      "created_at": "2026-04-26T01:00:00Z",
      "last_verified_at": "2026-04-26T01:15:00Z",
      "metadata": {}
    }
  ],
  "count": 1
}
```

---

## 11. Full Authentication Flow (End-to-End)

```bash
#!/bin/bash
set -e

BASE="http://localhost:8000/api"
ADMIN_JWT="your-admin-jwt"

# 1. Register agent
echo "1. Registering agent..."
RESP=$(curl -s -X POST "$BASE/agent-identities" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{"agent_id":"agent-demo","name":"Demo Agent","tenant_id":"demo"}')
SECRET=$(echo $RESP | jq -r '.secret_key')
API_KEY=$(echo $RESP | jq -r '.api_key')
echo "Secret: $SECRET"
echo "API Key: $API_KEY"

# 2. Authenticate
echo "2. Authenticating..."
curl -s -X POST "$BASE/agent-identities/agent-demo/authenticate" \
  -H "Content-Type: application/json" \
  -d "{\"secret_key\": \"$SECRET\"}" | jq

# 3. Operator verifies
echo "3. Verifying agent..."
curl -s -X POST "$BASE/agent-identities/agent-demo/verify" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{"verifier_id": "op-admin"}' | jq

# 4. Get trust score
echo "4. Trust score:"
curl -s "$BASE/agent-identities/agent-demo/trust" \
  -H "Authorization: Bearer $API_KEY" | jq

# 5. Issue capability
echo "5. Capability token:"
curl -s -X POST "$BASE/agent-identities/agent-demo/capability" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"action": "read", "resource": "public-data"}' | jq

echo "✅ Full flow complete"
```

---

## Python SDK Example

```python
import requests

class CitadelAgent:
    def __init__(self, base_url: str, agent_id: str, secret_key: str):
        self.base = base_url.rstrip("/")
        self.agent_id = agent_id
        self.secret_key = secret_key
        self.api_key = None

    def authenticate(self) -> dict:
        """Authenticate and store API key."""
        resp = requests.post(
            f"{self.base}/api/agent-identities/{self.agent_id}/authenticate",
            json={"secret_key": self.secret_key}
        )
        resp.raise_for_status()
        data = resp.json()
        # Note: real API returns api_key at registration, not auth
        return data

    def get_trust_snapshot(self, api_key: str) -> dict:
        """Get current trust snapshot."""
        resp = requests.get(
            f"{self.base}/api/agent-identities/{self.agent_id}/trust",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        resp.raise_for_status()
        return resp.json()

    def get_capability(self, api_key: str, action: str, resource: str) -> dict:
        """Request a capability token."""
        resp = requests.post(
            f"{self.base}/api/agent-identities/{self.agent_id}/capability",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"action": action, "resource": resource}
        )
        resp.raise_for_status()
        return resp.json()


# Usage
agent = CitadelAgent("http://localhost:8000", "agent-scraper-001", "ak_...")

# After registration, you have the api_key
trust = agent.get_trust_snapshot(api_key="ak_demo_...")
print(f"Trust: {trust['score']} ({trust['band']}) — {trust['snapshot_id']}")

cap = agent.get_capability(
    api_key="ak_demo_...",
    action="scrape",
    resource="https://example.com"
)
print(f"Capability: {cap['authorized']}")
```

---

## Error Codes

| Code | Meaning | Retry? |
|------|---------|--------|
| 200 | Success | — |
| 201 | Created (registration) | — |
| 401 | Invalid credentials | No — check secret/key |
| 404 | Agent identity not found | No — register first |
| 409 | Identity already registered | No — use existing or rotate |
| 503 | Database unavailable | Yes — with backoff |

---

## Migration from Fantasy API

| Old (CITADEL.*) | New (HTTP) |
|-----------------|------------|
| `CITADEL.agents.register(id, name)` | `POST /api/agent-identities` |
| `CITADEL.agents.authenticate(id, secret)` | `POST /api/agent-identities/{id}/authenticate` |
| `CITADEL.agents.verify(id, operator)` | `POST /api/agent-identities/{id}/verify` |
| `CITADEL.agents.revoke(id, reason)` | `POST /api/agent-identities/{id}/revoke` |
| `CITADEL.agents.getTrustScore(id)` | `GET /api/agent-identities/{id}/trust` |
| `CITADEL.agents.issueCapability(id, action)` | `POST /api/agent-identities/{id}/capability` |

---

**Document Owner:** Security Engineering  
**Review Cycle:** When API changes
