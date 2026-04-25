# OpenAI Agents SDK Integration

## What you'll learn

- Add CITADEL guardrails to OpenAI Agents SDK
- Govern tool execution in agent loops
- Configure per-agent policies
- Audit agent reasoning and actions

---

## Installation

```bash
npm install @citadel/sdk @citadel/sdk-openai
```

---

## Basic Integration

```typescript
import { Agent } from 'openai-agents';
import { CitadelGuardrail } from '@citadel/sdk-openai';

const CITADEL_BASE = 'https://api.citadelsdk.com/api';
const API_KEY = 'ak_demo_...';

const guardrail = new CitadelGuardrail({
  baseUrl: CITADEL_BASE,
  apiKey: API_KEY,
  agentId: 'openai-agent-01'
});

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

The CITADELGuardrail intercepts at three points:

1. Before tool execution: Evaluates tool call against policies
2. After tool execution: Validates output against post-conditions
3. On handoff: Authenticates agent-to-agent transfers

---

## Multi-Agent Orchestration

```typescript
import { handoff } from 'openai-agents';

const salesAgent = new Agent({ name: 'Sales', guardrails: [guardrail] });
const supportAgent = new Agent({ name: 'Support', guardrails: [guardrail] });

// Issue capability token for handoff
const resp = await fetch(`${CITADEL_BASE}/agent-identities/sales/capability`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${API_KEY}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'handoff', resource: 'support', context: {} })
});
const { token } = await resp.json();

await handoff({
  from: salesAgent,
  to: supportAgent,
  authToken: token  // Capability token from Citadel
});
```

---

## Next steps

- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
