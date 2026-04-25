# CrewAI Integration

## What you'll learn

- Install CITADEL's CrewAI task hooks
- Govern every task execution in your crew
- Inter-agent authentication with `gt_` tokens
- Configure crew-wide policies vs. per-agent policies

---

## Installation

```bash
pip install citadel-governance[crewai]
# or
pip install citadel-governance crewai
```

---

## Basic Integration

```python
from crewai import Agent, Task, Crew
from citadel.integrations.crewai import CITADELTaskHook

# Initialize CITADEL
import citadel
CITADEL = citadel.Client(api_key="ldk_test_...")

# Create CITADEL hook
citadel_hook = CITADELTaskHook(
    client=CITADEL,
    crew_id="research-crew-01"
)

# Define agents
researcher = Agent(
    role="Researcher",
    goal="Find information",
    tools=[search_tool],
    hooks=[citadel_hook]  # <-- Governance here
)

writer = Agent(
    role="Writer",
    goal="Write content",
    tools=[write_tool],
    hooks=[citadel_hook]
)

# Define tasks with governance
task1 = Task(
    description="Research topic",
    agent=researcher,
    hooks=[citadel_hook]
)

task2 = Task(
    description="Write article",
    agent=writer,
    hooks=[citadel_hook]
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
    hooks=[citadel_hook],
    metadata={
        "citadel_policy": "database-access-approval"
    }
)

# Low-risk task: allow
task_simple = Task(
    description="Search web",
    agent=researcher,
    hooks=[citadel_hook],
    metadata={
        "citadel_policy": "web-search-allow"
    }
)
```

---

## Inter-Agent Authentication

When agents hand off work, verify identity:

```python
# Agent A completes task, generates auth token
task_result = task1.execute()
auth_token = CITADEL.agents.authenticate(
    from_agent="researcher-01",
    to_agent="writer-01",
    task_id=task_result.id
)

# Agent B verifies before accepting
is_valid = CITADEL.agents.verify_auth(
    agent_id="writer-01",
    token=auth_token
)
```

---

## Next steps

- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
