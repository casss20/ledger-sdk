# Recipe: Multi-Agent Coordination

## What you'll learn

- Authenticate agent-to-agent communication using API keys
- Trace actions across agent chains with audit logs
- Govern handoffs between agents using approvals
- Audit multi-agent workflows

---

## Use Case
Your customer support pipeline uses three agents: triage → resolution → follow-up. Each handoff must be authenticated and audited.

---

## Architecture

```
Triage Agent
    ↓ [API Key + X-Tenant-ID]
Resolution Agent
    ↓ [API Key + X-Tenant-ID]
Follow-up Agent
    ↓ [Audit log]
Citadel Dashboard
```

---

## Implementation

### Step 1: Get API keys for each agent

Each agent needs its own API key. Create them via the dashboard or API:

```bash
# Create API key for triage agent
curl -X POST https://api.citadelsdk.com/auth/keys \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "triage-agent"}'

# Response:
# {"key_id": "gk_live_...", "key_secret": "secret_shown_once"}
```

### Step 2: Govern actions with Citadel

Each agent wraps its actions with the Citadel API:

```python
import requests

CITADEL_API = "https://api.citadelsdk.com"
HEADERS = {
    "X-API-Key": "gk_live_your_key_id",
    "X-API-Secret": "your_key_secret",
    "X-Tenant-ID": "your-tenant",
    "Content-Type": "application/json"
}

# Triage agent: create a governed action
response = requests.post(
    f"{CITADEL_API}/v1/actions",
    headers=HEADERS,
    json={
        "action_type": "ticket.triage",
        "payload": {
            "ticket_id": "ticket-123",
            "priority": "high",
            "category": "billing"
        },
        "agent_id": "triage-agent"
    }
)
action = response.json()
print(f"Action created: {action['action_id']}")

# Resolution agent: continue the workflow
response = requests.post(
    f"{CITADEL_API}/v1/actions",
    headers=HEADERS,
    json={
        "action_type": "ticket.resolve",
        "payload": {
            "ticket_id": "ticket-123",
            "resolution": "refund_approved"
        },
        "agent_id": "resolution-agent"
    }
)

# If approval is required, check the approval queue
approvals = requests.get(
    f"{CITADEL_API}/v1/approvals",
    headers=HEADERS
).json()
```

### Step 3: Trace across agents with metadata

Pass trace context through action metadata:

```python
import uuid

# Start a trace
trace_id = str(uuid.uuid4())

# Each agent includes trace_id in payload
triage_action = requests.post(
    f"{CITADEL_API}/v1/actions",
    headers=HEADERS,
    json={
        "action_type": "ticket.triage",
        "payload": {
            "ticket_id": "ticket-123",
            "trace_id": trace_id,
            "step": 1,
            "agent": "triage"
        }
    }
).json()

resolution_action = requests.post(
    f"{CITADEL_API}/v1/actions",
    headers=HEADERS,
    json={
        "action_type": "ticket.resolve",
        "payload": {
            "ticket_id": "ticket-123",
            "trace_id": trace_id,
            "step": 2,
            "agent": "resolution",
            "parent_action": triage_action["action_id"]
        }
    }
).json()
```

### Step 4: Audit the full workflow

Query the audit trail to see the complete agent chain:

```python
# Get all actions for a trace
audit = requests.get(
    f"{CITADEL_API}/v1/audit",
    headers=HEADERS,
    params={"trace_id": trace_id}
).json()

for event in audit["events"]:
    print(f"[{event['step']}] {event['agent']}: {event['action_type']} → {event['status']}")
```

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Core Concepts: Human Approvals](../core-concepts/human-approvals.md)
- [Recipe: Agent-to-Agent Authentication](agent-to-agent-authentication.md)
