# Custom Integration Guide

## What you'll learn

- Integrate Citadel with any agent framework
- Build custom middleware for your stack
- Handle governance errors in your application
- Best practices for production integrations

---

## Integration Pattern

Every integration follows the same pattern:

```
Agent requests action
    ↓
[YOUR MIDDLEWARE] Intercept
    ↓
Call citadel.govern()
    ↓
    ├─ ALLOWED → Execute original action
    ├─ DENIED → Return error to agent
    └─ APPROVAL_REQUIRED → Queue for review
    ↓
Return result to agent
```

---

## Building Custom Middleware

### Python middleware template

```python
import ledger_sdk

class CustomGovernanceMiddleware:
    def __init__(self, api_key, agent_id):
        self.citadel = ledger_sdk.Client(api_key=api_key)
        self.agent_id = agent_id

    def before_action(self, action, params):
        governed = self.citadel.govern(
            agent_id=self.agent_id,
            action=action,
            params=params
        )
        try:
            result = governed.execute()
            return {"allowed": True, "token": result.governance_token}
        except ledger_sdk.PolicyDeniedError as e:
            return {"allowed": False, "error": str(e)}
        except ledger_sdk.ApprovalRequiredError as e:
            return {"allowed": False, "approval_url": e.approval_url}

    def after_action(self, action, params, outcome, token):
        self.citadel.audit.record_outcome(
            governance_token=token,
            outcome=outcome
        )
```

### TypeScript middleware template

```typescript
import { CitadelClient, PolicyDeniedError, ApprovalRequiredError } from '@citadel/sdk';

class CustomGovernanceMiddleware {
  private citadel: CitadelClient;
  private agentId: string;

  constructor(apiKey: string, agentId: string) {
    this.citadel = new CitadelClient({ apiKey });
    this.agentId = agentId;
  }

  async beforeAction(action: string, params: any) {
    const governed = this.citadel.govern({
      agentId: this.agentId,
      action,
      params
    });
    try {
      const result = await governed.execute();
      return { allowed: true, token: result.governanceToken };
    } catch (error) {
      if (error instanceof PolicyDeniedError) {
        return { allowed: false, error: error.message };
      }
      if (error instanceof ApprovalRequiredError) {
        return { allowed: false, approvalUrl: error.approvalUrl };
      }
      throw error;
    }
  }
}
```

---

## Handling Errors

### Graceful degradation

```python
def safe_execute(action, params):
    try:
        result = middleware.before_action(action, params)
        if not result["allowed"]:
            logger.warning(f"Action blocked: {result.get('error')}")
            return None
        outcome = execute_original_action(action, params)
        middleware.after_action(action, params, outcome, result["token"])
        return outcome
    except Exception as e:
        logger.error(f"Governance check failed: {e}")
        if ALLOW_FALLBACK:
            return execute_original_action(action, params)
        raise
```

---

## Testing Your Integration

```python
def test_middleware():
    middleware = CustomGovernanceMiddleware("ldk_test_...", "test-agent")
    result = middleware.before_action("safe.action", {})
    assert result["allowed"] is True
    result = middleware.before_action("dangerous.action", {})
    assert result["allowed"] is False
    print("All tests passed")
```

---

## Next steps

- [API Reference: Python SDK](../api-reference/python-sdk.md)
- [API Reference: TypeScript SDK](../api-reference/typescript-sdk.md)
- [Security Best Practices](../guides/security-best-practices.md)
