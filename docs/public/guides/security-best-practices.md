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

Forward to SIEM:
```bash
curl -X POST https://api.citadelsdk.com/api/v1/webhooks \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://siem.company.com/citadel",
    "events": ["kill_switch.activated", "policy.modified", "agent_identity.revoked"]
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

## Next steps

- [Production Deployment](production-deployment.md)
- [Incident Response](incident-response.md)
