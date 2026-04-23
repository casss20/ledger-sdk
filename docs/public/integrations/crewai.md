# CrewAI Integration

## What you'll learn

- Install Ledger's CrewAI task hooks
- Govern every task execution in your crew
- Inter-agent authentication with `gt_` tokens
- Configure crew-wide policies vs. per-agent policies

---

## Installation

```bash
pip install ledger-sdk[crewai]
# or
pip install ledger-sdk crewai
```

---

## Basic Integration

```python
from crewai import Agent, Task, Crew
from ledger_sdk.integrations.crewai import LedgerTaskHook

# Initialize Ledger
import ledger_sdk
ledger = ledger_sdk.Client(api_key="ldk_test_...")

# Create Ledger hook
ledger_hook = LedgerTaskHook(
    client=ledger,
    crew_id="research-crew-01"
)

# Define agents
researcher = Agent(
    role="Researcher",
    goal="Find information",
    tools=[search_tool],
    hooks=[ledger_hook]  # <-- Governance here
)

writer = Agent(
    role="Writer",
    goal="Write content",
    tools=[write_tool],
    hooks=[ledger_hook]
)

# Define tasks with governance
task1 = Task(
    description="Research topic",
    agent=researcher,
    hooks=[ledger_hook]
)

task2 = Task(
    description="Write article",
    agent=writer,
    hooks=[ledger_hook]
)

# Create crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2]
)

result = crew.kickoff()
```

---

## Task-Level Governance

Different tasks, different policies:

```python
# High-risk task: requires approval
task_sensitive = Task(
    description="Access customer database",
    agent=researcher,
    hooks=[ledger_hook],
    metadata={
        "ledger_policy": "database-access-approval"
    }
)

# Low-risk task: allow
task_simple = Task(
    description="Search web",
    agent=researcher,
    hooks=[ledger_hook],
    metadata={
        "ledger_policy": "web-search-allow"
    }
)
```

---

## Inter-Agent Authentication

When agents hand off work, verify identity:

```python
# Agent A completes task, generates auth token
task_result = task1.execute()
auth_token = ledger.agents.authenticate(
    from_agent="researcher-01",
    to_agent="writer-01",
    task_id=task_result.id
)

# Agent B verifies before accepting
is_valid = ledger.agents.verify_auth(
    agent_id="writer-01",
    token=auth_token
)
```

---

## Next steps

- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
