# Rate Limits

## Tiers

| Tier | Daily Limit | Burst | Cost |
|------|-------------|-------|------|
| Free | 1,000 | 10/min | $0 |
| Pro | 100,000 | 1,000/min | $49/mo |
| Enterprise | Unlimited | Custom | Contact |

## Headers

Every response includes rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1713862800
```

## Handling 429

```python
try:
    result = action.execute()
except citadel.RateLimitError as e:
    time.sleep(e.retry_after)
    result = action.execute()  # Retry
```

## Increasing Limits

Upgrade at [dashboard.CITADEL.dev](https://dashboard.CITADEL.dev) or contact sales@CITADEL.dev for Enterprise.
