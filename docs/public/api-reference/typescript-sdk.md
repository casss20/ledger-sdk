# TypeScript SDK Reference

## Installation

```bash
npm install @citadel/sdk
```

## Client

```typescript
import { CITADELClient } from '@citadel/sdk';

const CITADEL = new CITADELClient({
  apiKey: 'ldk_test_...',
  environment: 'sandbox'
});
```

## Govern Actions

```typescript
const action = citadel.govern({
  agentId: 'agent-123',
  action: 'email.send',
  params: { to: 'user@example.com', subject: 'Welcome' }
});

const result = await action.execute();
```

## Exception Handling

| Exception | When |
|-----------|------|
| `PolicyDeniedError` | Action blocked |
| `ApprovalRequiredError` | Needs human review |
| `RateLimitError` | Too many requests |
| `KillSwitchActivatedError` | Agent stopped |

## Audit

```typescript
const records = await CITADEL.audit.query({ agentId: 'agent-123', limit: 100 });
const record = await CITADEL.audit.get('gt_...');
const isValid = await CITADEL.audit.verifyChain(record);
```

## Kill Switch

```typescript
await CITADEL.killSwitch.activate({ agentId: 'agent-123', reason: '...', duration: '1h' });
await CITADEL.killSwitch.deactivate({ agentId: 'agent-123', reason: '...' });
```

## Approvals

```typescript
const pending = await CITADEL.approvals.list({ status: 'pending' });
await CITADEL.approvals.approve({ approvalId: 'app_...', reason: 'Verified' });
await CITADEL.approvals.deny({ approvalId: 'app_...', reason: 'Suspicious' });
```
