# Getting Started with Ledger SDK for TypeScript/Node.js

## What you'll learn

- Install Ledger SDK via npm in under 60 seconds
- Wrap your first async agent action with governance
- Understand how `gt_` tokens track every decision
- View governed actions in the Ledger dashboard
- Connect Ledger to an OpenAI Agents SDK project

## Prerequisites

- Node.js 18 or higher
- TypeScript 5.0+ (optional but recommended)
- A Ledger API key ([get one free](https://dashboard.ledger.dev))

> 💡 **New to governance?** Ledger embeds compliance directly into your agent runtime. Every tool call passes through the Ledger kernel before execution — making governance non-bypassable and automatic.

---

## Step 1: Install Ledger SDK

```bash
npm install @ledger/sdk
# or
yarn add @ledger/sdk
# or
pnpm add @ledger/sdk
```

Verify the installation:

```bash
node -e "const ledger = require('@ledger/sdk'); console.log(ledger.VERSION)"
```

> ⚠️ **Note:** If you see `Cannot find module`, ensure your `package.json` includes `"type": "module"` for ESM, or use `require()` for CommonJS.

---

## Step 2: Configure your environment

Create a `.env` file:

```bash
LEDGER_API_KEY=ldk_test_xxxxxxxxxxxxxxxx
LEDGER_ENVIRONMENT=sandbox
```

Load it in your application:

```typescript
import 'dotenv/config';
```

> 💡 **Environment tip:** Use `sandbox` for development (unlimited actions, no billing). Switch to `production` when deploying.

---

## Step 3: Initialize the client

```typescript
import { LedgerClient } from '@ledger/sdk';

const ledger = new LedgerClient({
  apiKey: process.env.LEDGER_API_KEY!,
  environment: 'sandbox'
});

// Verify connectivity
await ledger.ping();
console.log('Connected to Ledger sandbox');
```

---

## Step 4: Govern your first action

```typescript
// Define what your agent wants to do
const action = ledger.govern({
  agentId: 'email-agent-01',
  action: 'email.send',
  params: {
    to: 'user@example.com',
    subject: 'Welcome to our platform',
    body: 'Thanks for signing up!'
  }
});

// Execute with automatic policy enforcement
try {
  const result = await action.execute();
  console.log(`Action allowed: ${result.governanceToken}`);
} catch (error) {
  if (error instanceof PolicyDeniedError) {
    console.log(`Action denied: ${error.policyName}`);
  } else if (error instanceof ApprovalRequiredError) {
    console.log(`Waiting for approval: ${error.approvalUrl}`);
  }
}
```

**What just happened:**
1. Ledger evaluated the action against all active policies
2. If allowed, it returned a governance token (`gt_...`)
3. If denied, it threw `PolicyDeniedError`
4. If approval required, it threw `ApprovalRequiredError` with a review URL

---

## Step 5: Understanding `gt_` tokens

```typescript
const result = await action.execute();
console.log(result.governanceToken); // gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh
```

These tokens are:
- **Immutable**: Cannot be altered or deleted once created
- **Non-portable**: Only resolvable by Ledger's vault
- **Traceable**: Link into a hash chain for audit
- **Referencable**: Query the audit trail later

Query by token:

```typescript
const record = await ledger.audit.get('gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh');
console.log(record.decision);     // "allowed"
console.log(record.policyName);   // "email-sending-allowed"
console.log(record.timestamp);    // ISO 8601
```

---

## Step 6: Connect to OpenAI Agents SDK

```typescript
import { Agent } from 'openai-agents';
import { LedgerOpenAIIntegration } from '@ledger/sdk/integrations';

const ledgerIntegration = new LedgerOpenAIIntegration({
  client: ledger,
  agentId: 'openai-agent-01'
});

const agent = new Agent({
  name: 'EmailAgent',
  instructions: 'Send emails to users',
  tools: [sendEmailTool],
  guardrails: [ledgerIntegration.guardrail()] // <-- Governance here
});

const result = await agent.run('Send welcome email to new@user.com');
```

---

## Step 7: View in dashboard

Open [Ledger Dashboard](https://dashboard.ledger.dev) → **Activity Stream**.

Filter by agent ID:
```
agentId:email-agent-01
```

Or governance token:
```
gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh
```

---

## Troubleshooting

### "API key invalid"
Keys start with `ldk_test_` (sandbox) or `ldk_live_` (production). Generate new keys at [dashboard.ledger.dev](https://dashboard.ledger.dev).

### "Policy denied all actions"
New projects start with default deny-all. Create an allow policy:
```typescript
await ledger.policies.create({
  name: 'allow-email',
  trigger: { action: 'email.send' },
  enforcement: { type: 'allow' }
});
```

### High latency on first call
First call incurs ~50ms for policy compilation. Subsequent calls use cached policies and take <5ms.

### TypeScript type errors
Ensure `@ledger/sdk` types are installed: `npm install -D @ledger/sdk-types`

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
- [Recipe: Email Sending Rate Limit](../recipes/email-sending-rate-limit.md)
- [Integration: OpenAI Agents SDK](../integrations/openai-agents.md)
