# Security Best Practices

## What you'll learn

- Secure your Citadel deployment
- Manage API keys
- Configure network security
- Audit security events

---

## API Key Management

### Rotate keys every 90 days
```bash
citadel keys rotate --env production
```

### Use separate keys per environment
- `ldk_test_*` — Development only
- `ldk_live_*` — Production only
- Never commit keys to version control

### Enable key restrictions
```python
citadel.config.set_key_restrictions(
    ip_allowlist=["10.0.0.0/8"],
    time_window={"start": "08:00", "end": "18:00"}
)
```

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
- `key.rotated`
- `approver.delegated`

Forward to SIEM:
```python
citadel.config.set_webhook(
    url="https://siem.company.com/citadel",
    events=["kill_switch.activated", "policy.modified"]
)
```

---

## Kill Switch Testing

Test monthly in staging:
```bash
citadel kill-switch test --env staging --scope all
```

---

## Next steps

- [Production Deployment](production-deployment.md)
- [Incident Response](incident-response.md)
