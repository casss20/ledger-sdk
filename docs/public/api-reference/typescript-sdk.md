# TypeScript SDK Reference

## Installation

```bash
npm install @ledger/sdk
```

## Client

```typescript
import { LedgerClient } from '@ledger/sdk';

const ledger = new LedgerClient({
  apiKey: 'ldk_test_...',
  environment: 'sandbox'
});
```

## Govern Actions

```typescript
const action = ledger.govern({
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
const records = await ledger.audit.query({ agentId: 'agent-123', limit: 100 });
const record = await ledger.audit.get('gt_...');
const isValid = await ledger.audit.verifyChain(record);
```

## Kill Switch

```typescript
await ledger.killSwitch.activate({ agentId: 'agent-123', reason: '...', duration: '1h' });
await ledger.killSwitch.deactivate({ agentId: 'agent-123', reason: '...' });
```

## Approvals

```typescript
const pending = await ledger.approvals.list({ status: 'pending' });
await ledger.approvals.approve({ approvalId: 'app_...', reason: 'Verified' });
await ledger.approvals.deny({ approvalId: 'app_...', reason: 'Suspicious' });
```
