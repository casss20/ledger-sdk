# Recipe: Email Sending Rate Limit

## What you'll learn

- Throttle agent email sending
- Prevent spam and blacklisting
- Configure burst limits
- Handle rate limit errors

---

## Use Case
Your marketing agent sends welcome emails to new users. Without limits, a bug could trigger thousands of emails, getting your domain blacklisted.

---

## Policy

```yaml
apiVersion: ledger.gov/v1
kind: Policy
metadata:
  name: email-rate-limit
  namespace: marketing
spec:
  trigger:
    action: email.send
  enforcement:
    type: rate_limit
    limit: 100
    window: 1h
    burst: 20
  audit:
    level: standard
```

---

## SDK Implementation

```python
# Send multiple emails
for user in new_users:
    try:
        action = ledger.govern(
            agent_id="welcome-agent",
            action="email.send",
            params={"to": user.email, "template": "welcome"}
        )
        result = action.execute()
    except ledger_sdk.RateLimitError as e:
        print(f"Rate limit hit. Retry after {e.retry_after}s")
        time.sleep(e.retry_after)
```

---

## Monitoring

```python
# Check rate limit status
status = ledger.rate_limits.get_status(
    agent_id="welcome-agent",
    action="email.send"
)
print(f"Used: {status.used}/{status.limit}")
print(f"Resets at: {status.reset_time}")
```

---

## Next steps

- [API Reference: Rate Limits](../api-reference/rate-limits.md)
- [Recipe: Database Write Protection](database-write-protection.md)
