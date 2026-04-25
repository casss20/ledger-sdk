# Getting Started with Citadel SDK for Python

## What you'll learn

- Install Citadel SDK in under 60 seconds
- Wrap your first agent action with governance
- Understand how `gt_` tokens track every decision
- View your governed actions in the Citadel dashboard
- Connect Citadel to a real LangChain agent

## Prerequisites

- Python 3.9 or higher
- A Citadel API key ([get one free](https://dashboard.citadel.dev))
- Basic familiarity with Python async/await (optional but recommended)

> 💡 **New to governance?** Citadel embeds compliance directly into your agent runtime. Every tool call passes through the Citadel kernel before execution — making governance non-bypassable and automatic.

---

## Step 1: Install Citadel SDK

```bash
pip install citadel-governance
```

Verify the installation:

```bash
python -c "import citadel; print(citadel.__version__)"
```

> ⚠️ **Note:** If you see `ModuleNotFoundError`, ensure your virtual environment is activated:
> ```bash
> python -m venv .venv && source .venv/bin/activate  # Linux/Mac
> python -m venv .venv && .venv\Scripts\activate    # Windows
> ```

---

## Step 2: Configure your environment

Create a `.env` file in your project root:

```bash
CITADEL_API_KEY=ldk_test_xxxxxxxxxxxxxxxx
CITADEL_ENVIRONMENT=sandbox
```

Load it in Python:

```python
from dotenv import load_dotenv
load_dotenv()
```

> 💡 **Environment tip:** Use `sandbox` for development (unlimited actions, no billing). Switch to `production` when you're ready to deploy.

---

## Step 3: Initialize the client

```python
import citadel

client = citadel.CitadelClient(
    base_url="https://api.citadel.dev",
    api_key="ldk_live_xxxxxxxxxxxxxxxx"
)

# Verify connectivity
await client.ping()
print("Connected to Citadel production")
```

---

## Step 4: Govern your first action

The core pattern: wrap any agent action with `citadel.govern()` before executing it.

```python
# Define what your agent wants to do
action = citadel.govern(
    agent_id="email-agent-01",
    action="email.send",
    params={
        "to": "user@example.com",
        "subject": "Welcome to our platform",
        "body": "Thanks for signing up!"
    }
)

# Execute with automatic policy enforcement
try:
    result = await client.execute(
        action="email.send",
        resource="user@example.com",
        actor_id="agent-01"
    )
    print(f"Action allowed: {result.decision.decision_id}")
except Exception as e:
    # Handle 402 (Payment Required) or 429 (Quota Exceeded)
    print(f"Action blocked: {e}")
```

**What just happened:**
1. Citadel evaluated your action against all active policies
2. If allowed, it returned a governance token (`gt_...`) — an immutable reference to this decision
3. If denied, it raised `PolicyDeniedError` with the blocking policy name
4. If approval is required, it returned an approval URL for human review

---

## Step 5: Understanding `gt_` tokens

Every governed action receives a unique governance token:

```python
result = action.execute()
print(result.governance_token)  # gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh
```

These tokens are:
- **Immutable**: Once created, they cannot be altered or deleted
- **Non-portable**: Only resolvable by Citadel's vault (like Stripe's `pm_` tokens)
- **Traceable**: Link together into a hash chain for audit purposes
- **Referencable**: Use them to query the audit trail later

Query an action by its token:

```python
audit_record = citadel.audit.get("gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh")
print(audit_record.decision)      # "allowed"
print(audit_record.policy_name)   # "email-sending-allowed"
print(audit_record.timestamp)     # ISO 8601 timestamp
```

---

## Step 6: Connect to LangChain

Citadel integrates seamlessly with LangChain via a callback handler:

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from citadel.integrations.langchain import CitadelCallbackHandler

# Initialize Citadel handler
citadel_handler = CitadelCallbackHandler(
    client=citadel,
    agent_id="langchain-agent-01"
)

# Create your agent with the handler
llm = ChatOpenAI(model="gpt-4")
tools = [search_tool, calculator_tool, email_tool]
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[ledger_handler]  # <-- This enables governance
)

# Every tool call now passes through Citadel
result = agent_executor.invoke({"input": "Send a welcome email to new@user.com"})
```

> 💡 **What happens:** The `LedgerCallbackHandler` intercepts every tool call before it reaches the tool implementation. Citadel evaluates the call against your policies, logs the decision, and either allows execution or raises an exception.

---

## Step 7: View in dashboard

Open the [Citadel Dashboard](https://dashboard.citadel.dev) and navigate to **Activity Stream**.

You'll see:
- Every action your agent attempted
- The decision (allowed/denied/approval-required)
- The policy that evaluated it
- The full hash chain for tamper verification

Filter by agent ID:
```
agent_id:email-agent-01
```

Or by governance token:
```
gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh
```

---

## Troubleshooting

### "API key invalid" error
Verify your key starts with `ldk_test_` for sandbox or `ldk_live_` for production. Generate a new key at [dashboard.citadel.dev](https://dashboard.citadel.dev).

### "Policy denied all actions"
New projects start with a default deny-all policy. Create an allow policy:
```python
citadel.policies.create({
    "name": "allow-email",
    "trigger": {"action": "email.send"},
    "enforcement": {"type": "allow"}
})
```

### High latency on first call
The first governed call incurs ~50ms for policy compilation. Subsequent calls use cached policies and take <5ms.

### Dashboard not showing actions
Ensure your `agent_id` matches between code and dashboard filter. Agent IDs are case-sensitive.

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md) — Deep dive into `gt_` tokens
- [Core Concepts: Policies](../core-concepts/policies.md) — Write your first YAML policy
- [Recipe: Email Sending Rate Limit](../recipes/email-sending-rate-limit.md) — Prevent email spam
- [Integration: LangChain](../integrations/langchain.md) — Full LangChain integration guide

**Questions?** Join our [Discord community](https://discord.gg/citadel) or email support@citadel.dev.
