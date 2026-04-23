# Webhook Events

## Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `governance.action.allowed` | Action passed | `{agent_id, action, gt_token}` |
| `governance.action.denied` | Action blocked | `{agent_id, action, policy, reason}` |
| `governance.approval.required` | Approval queued | `{approval_id, agent_id, approvers}` |
| `governance.approval.decided` | Approval resolved | `{approval_id, decision, approver}` |
| `governance.kill_switch.activated` | Emergency stop | `{scope, target, reason}` |
| `governance.kill_switch.deactivated` | System resumed | `{scope, target, reason}` |
| `governance.trust_score.changed` | Score updated | `{agent_id, old_score, new_score}` |
| `governance.audit.exported` | Export ready | `{export_id, format, url}` |

## Receiving Webhooks

Configure endpoint:
```python
ledger.webhooks.create(
    url="https://your-app.com/webhooks/ledger",
    events=["governance.action.denied", "governance.approval.required"],
    secret="whsec_..."
)
```

Verify signature:
```python
ledger.webhooks.verify(payload, signature, secret="whsec_...")
```

## Retry Policy

Failed deliveries retried with exponential backoff: 1s, 2s, 4s, 8s, 16s, then abandoned.

## Next steps

- [Security Best Practices](../guides/security-best-practices.md)
