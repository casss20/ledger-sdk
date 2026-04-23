# Migrating from Manual Logging

## What you'll learn

- Replace manual `print()` and `logger.info()` with Ledger
- Gain automatic policy enforcement
- Preserve existing log formats
- Migrate incrementally

---

## Before and After

### Before (manual logging)
```python
def send_email(to, subject, body):
    logger.info(f"Sending email to {to}")
    try:
        result = smtp.send(to, subject, body)
        logger.info(f"Email sent: {result}")
        return result
    except Exception as e:
        logger.error(f"Email failed: {e}")
        raise
```

### After (Ledger governance)
```python
def send_email(to, subject, body):
    action = ledger.govern(
        agent_id="email-agent",
        action="email.send",
        params={"to": to, "subject": subject, "body": body}
    )
    result = action.execute()  # Automatic logging + policy enforcement
    return result
```

---

## Incremental Migration

### Phase 1: Wrap high-risk actions only
```python
# Only govern the most sensitive operations
 governed_send = ledger.govern(...)
 # Keep manual logging for low-risk ops
```

### Phase 2: Add policies for wrapped actions
```yaml
apiVersion: ledger.gov/v1
kind: Policy
metadata:
  name: email-policy
spec:
  trigger:
    action: email.send
  enforcement:
    type: rate_limit
    limit: 100
    window: 1h
```

### Phase 3: Wrap all actions
Gradually replace manual logging with `ledger.govern()` for all agent actions.

### Phase 4: Remove manual logging
Once all actions are governed, remove legacy logging code.

---

## Next steps

- [Getting Started: Python](../getting-started/GETTING_STARTED_PYTHON.md)
- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
