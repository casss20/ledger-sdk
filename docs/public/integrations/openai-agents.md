# OpenAI Agents SDK Integration

## What you'll learn

- Add Ledger guardrails to OpenAI Agents SDK
- Govern tool execution in agent loops
- Configure per-agent policies
- Audit agent reasoning and actions

---

## Installation

```bash
npm install @ledger/sdk @ledger/sdk-openai
```

---

## Basic Integration

```typescript
import { Agent } from 'openai-agents';
import { LedgerGuardrail } from '@ledger/sdk-openai';

const ledger = new LedgerClient({ apiKey: 'ldk_test_...' });

const guardrail = new LedgerGuardrail({ client: ledger, agentId: 'openai-agent-01' });

const agent = new Agent({
  name: 'EmailAgent',
  instructions: 'Send emails to users',
  tools: [sendEmailTool],
  guardrails: [guardrail]
});

const result = await agent.run('Send welcome email to new@user.com');
```

---

## Guardrail Behavior

The LedgerGuardrail intercepts at three points:

1. Before tool execution: Evaluates tool call against policies
2. After tool execution: Validates output against post-conditions
3. On handoff: Authenticates agent-to-agent transfers

---

## Multi-Agent Orchestration

```typescript
import { handoff } from 'openai-agents';

const salesAgent = new Agent({ name: 'Sales', guardrails: [guardrail] });
const supportAgent = new Agent({ name: 'Support', guardrails: [guardrail] });

await handoff({
  from: salesAgent,
  to: supportAgent,
  authToken: ledger.agents.authenticate('sales', 'support')
});
```

---

## Next steps

- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
