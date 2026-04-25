# Citadel × K2.6 (Moonshot AI) Integration

Govern K2.6 agents with Citadel's policy engine, approval workflows, and audit trails.

## Installation

```bash
pip install citadel-governance moonshot-ai  # K2.6 SDK
```

## Quick Start

```python
import citadel
from citadel.integrations.k2_6 import GovernedK26Agent, GovernedK26Task

# 1. Create a governed agent
agent = GovernedK26Agent(
    citadel_client=citadel.CitadelClient(),
    name="data-analyst",
    description="Analyzes sensitive data safely",
)

# 2. Define a governed task
task = GovernedK26Task(
    citadel_client=citadel.CitadelClient(),
    name="analyze",
    action="data.analyze",
    agent=agent,
)

# 3. Execute with automatic policy enforcement
result = await task.execute(
    payload={"dataset": "users", "query": "count active"},
    actor_id="agent-1",
)
```

## GovernedK26Agent

Wraps a K2.6 agent with pre-flight governance checks.

```python
from citadel.integrations.k2_6 import GovernedK26Agent

agent = GovernedK26Agent(
    citadel_client=client,          # CitadelClient instance
    name="agent-name",               # Unique agent identifier
    description="What it does",      # Human-readable description
    metadata={                       # Extra context for policies
        "team": "analytics",
        "clearance": "level-2",
    },
)
```

### Methods

| Method | Description |
|--------|-------------|
| `check_policy(action, resource, payload)` | Pre-flight policy check |
| `execute(action, payload, actor_id)` | Execute with governance |
| `get_compliance_report()` | Generate audit trail summary |

## GovernedK26Task

Individual task with fine-grained governance.

```python
task = GovernedK26Task(
    citadel_client=client,
    name="email-send",
    action="email.send",
    agent=agent,
    requires_approval=True,  # Force human approval
)

result = await task.execute(
    payload={"to": "user@example.com", "subject": "Report"},
    actor_id="agent-1",
)
```

**Returns:**
- `{"status": "executed", "result": ...}` — Allowed and executed
- `{"status": "blocked", "reason": ...}` — Blocked by policy
- `{"status": "pending_approval", "approval_id": ...}` — Awaiting human review

## GovernedK26Workflow

Orchestrate multiple tasks with workflow-level governance.

```python
from citadel.integrations.k2_6 import GovernedK26Workflow

workflow = GovernedK26Workflow(
    citadel_client=client,
    name="onboarding",
    description="New user onboarding flow",
)

workflow.add_task(
    name="validate-email",
    action="email.validate",
    agent=validation_agent,
)
workflow.add_task(
    name="create-profile",
    action="profile.create",
    agent=profile_agent,
    depends_on=["validate-email"],
)

results = await workflow.execute(actor_id="agent-1")
```

## K26GovernanceServer

FastAPI server exposing governance tools.

```python
from fastapi import FastAPI
from citadel.integrations.k2_6 import K26GovernanceServer

app = FastAPI()
governance = K26GovernanceServer(citadel_client=client)
app.include_router(governance.router, prefix="/governance")
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/governance/check` | POST | Check if action is allowed |
| `/governance/kill` | POST | Emergency kill switch |
| `/governance/log` | POST | Log action for audit |
| `/governance/compliance` | GET | Compliance report |

## Configuration

Environment variables:

```bash
CITADEL_URL=http://localhost:8000
CITADEL_API_KEY=your-api-key
CITADEL_ACTOR_ID=default-agent
```

## Error Handling

```python
from citadel.core.sdk import ActionBlocked, ApprovalRequired

try:
    result = await task.execute(...)
except ActionBlocked as e:
    print(f"Blocked: {e.reason}")
except ApprovalRequired as e:
    print(f"Pending approval: {e.approval_id}")
```

## Compliance

All K2.6 actions are automatically logged to Citadel's audit trail with:
- Action ID and timestamp
- Actor identity
- Policy decision (allowed/blocked/pending)
- Full payload (hashed for sensitive data)
- Hash-chained integrity verification

## See Also

- [Citadel SDK Quick Start](../getting-started/GETTING_STARTED_PYTHON.md)
- [Governance Policies](../core-concepts/policies.md)
- [LangGraph Integration](langgraph.md)
