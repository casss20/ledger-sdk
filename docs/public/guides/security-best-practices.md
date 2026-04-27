# Security Best Practices

## What you'll learn

- Secure your Citadel deployment
- Manage API keys
- Configure network security
- Audit security events

---

## API Key Management

### Register an agent and get an API key
```bash
curl -X POST https://api.citadelsdk.com/api/agent-identities \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"my-agent","name":"My Agent","tenant_id":"demo"}'
```

### Rotate agent credentials
```bash
curl -X POST https://api.citadelsdk.com/api/agent-identities/my-agent/revoke \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Scheduled rotation"}'
```

### Use separate keys per environment
- `dev_tenant` — Development only
- `prod_tenant` — Production only
- Never commit keys to version control

### Enable key restrictions
Restrict by tenant_id and IP at the middleware level in `citadel/api/middleware.py`.

---

## Network Security

- Use TLS 1.3 for all API calls
- Enable mutual TLS (mTLS) for agent authentication
- Configure VPC peering for private connectivity
- Use Cloudflare or AWS WAF for DDoS protection

---

## Audit Security Events

Monitor these events:
- `kill_switch.activated`
- `policy.modified`
- `agent_identity.revoked`
- `approver.delegated`
- `trust_band.changed` (REVOKED, PROBATION transitions)
- `trust_override` (operator manually set band)
- `trust_circuit_breaker` (emergency REVOKED staging)
- `trust_probation.extended`

Forward to SIEM:
```bash
curl -X POST https://api.citadelsdk.com/api/v1/webhooks \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://siem.company.com/citadel",
    "events": [
      "kill_switch.activated",
      "policy.modified",
      "agent_identity.revoked",
      "trust_band.changed",
      "trust_override",
      "trust_circuit_breaker"
    ]
  }'
```

---

## Kill Switch Testing

Test monthly in staging:
```bash
curl -X POST https://api.citadelsdk.com/api/v1/governance/kill-switch/test \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"scope": "staging", "dry_run": true}'
```

---

## Trust Kill Switch Testing

Test the trust-based circuit breaker in staging:

```bash
# 1. Create a test agent with low score
curl -X POST https://api.citadelsdk.com/api/v1/trust/operator-override \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent",
    "target_band": "REVOKED",
    "reason": "Kill switch + trust integration test"
  }'

# 2. Verify kill switch is active
curl -X GET https://api.citadelsdk.com/api/v1/trust/snapshot/test-agent \
  -H "Authorization: Bearer $ADMIN_JWT"

# 3. Attempt action (should fail with LEDGER_005)
curl -X POST https://api.citadelsdk.com/api/v1/govern \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent",
    "action": "email.send",
    "params": {"to": "test@example.com"}
  }'

# 4. Restore agent to probation
curl -X POST https://api.citadelsdk.com/api/v1/trust/operator-override \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent",
    "target_band": "PROBATION",
    "reason": "Test complete — restored to probation"
  }'
```

---

## Next steps

- [Production Deployment](production-deployment.md)
- [Incident Response](incident-response.md)
