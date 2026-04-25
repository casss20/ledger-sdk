# Citadel × LangGraph Integration

Govern LangGraph state machines with Citadel's policy engine at every node transition.

## Installation

```bash
pip install citadel-governance langgraph
```

## Quick Start

```python
import citadel
from citadel.integrations.langgraph import GovernedNode, GovernedStateGraph
from langgraph.graph import StateGraph

# 1. Define your state
class AgentState(dict):
    pass

# 2. Create governed nodes
@GovernedNode(
    citadel_client=citadel.CitadelClient(),
    action="research.web_search",
)
async def search_node(state: AgentState):
    """Web search with automatic governance."""
    results = await web_search(state["query"])
    return {"results": results}

@GovernedNode(
    citadel_client=citadel.CitadelClient(),
    action="email.send",
    requires_approval=True,
)
async def notify_node(state: AgentState):
    """Email notification requires approval."""
    await send_email(state["recipient"], state["message"])
    return {"sent": True}

# 3. Build governed graph
graph = GovernedStateGraph(
    citadel_client=citadel.CitadelClient(),
    state_schema=AgentState,
)
graph.add_node("search", search_node)
graph.add_node("notify", notify_node)
graph.add_edge("search", "notify")
graph.set_entry_point("search")

# 4. Compile and run
app = graph.compile()
result = await app.ainvoke({"query": "AI governance"})
```

## GovernedNode

Decorator that wraps any LangGraph node with policy checks.

```python
from citadel.integrations.langgraph import GovernedNode

@GovernedNode(
    citadel_client=client,
    action="action.name",          # Policy action identifier
    resource="resource:id",         # Optional resource scope
    requires_approval=False,        # Force approval gate
    metadata={"team": "research"},  # Extra policy context
)
async def my_node(state):
    # Your node logic here
    return {"key": "value"}
```

### How It Works

1. **Pre-flight:** Before executing, calls `citadel.decide()`
2. **Blocked?** Returns `{"__blocked": True, "reason": ...}` — graph handles gracefully
3. **Pending approval?** Raises `ApprovalRequired` — catch in orchestration layer
4. **Allowed?** Executes your function and logs the action

## GovernedStateGraph

Graph-level governance with node orchestration.

```python
from citadel.integrations.langgraph import GovernedStateGraph

graph = GovernedStateGraph(
    citadel_client=client,
    state_schema=AgentState,
    name="research-workflow",
    description="Multi-step research with governance",
)

# Add nodes (can be governed or regular)
graph.add_node("search", search_node)
graph.add_node("analyze", analyze_node)
graph.add_node("report", report_node)

# Define edges
graph.add_edge("search", "analyze")
graph.add_edge("analyze", "report")

# Conditional routing with governance
graph.add_conditional_edges(
    "analyze",
    route_based_on_confidence,
    {
        "high": "report",
        "low": "search",  # Loop back for more research
    },
)
```

### Graph-Level Controls

```python
# Kill switch — immediately halt all node execution
await graph.kill_switch(reason="Policy violation detected")

# Check if graph is healthy
status = await graph.health_check()
# {"status": "healthy", "blocked_nodes": [], "pending_approvals": 0}

# Get compliance report
report = await graph.compliance_report()
# {"total_nodes": 5, "executed": 4, "blocked": 1, "audit_hash": "abc123..."}
```

## Handling Blocked Nodes

When a node is blocked, the graph returns a special state:

```python
result = await app.ainvoke({"query": "sensitive topic"})

if result.get("__blocked"):
    print(f"Node blocked: {result['__reason']}")
    print(f"Policy: {result['__winning_rule']}")
    # Handle gracefully — don't crash the workflow
```

## LangGraphGovernanceServer

FastAPI server for external governance control.

```python
from fastapi import FastAPI
from citadel.integrations.langgraph import LangGraphGovernanceServer

app = FastAPI()
governance = LangGraphGovernanceServer(citadel_client=client)
app.include_router(governance.router, prefix="/langgraph")
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/langgraph/check` | POST | Check node action |
| `/langgraph/kill` | POST | Emergency stop |
| `/langgraph/log` | POST | Log node execution |
| `/langgraph/compliance` | GET | Full audit report |

## Best Practices

### 1. Action Naming

Use consistent action names for policy rules:

```python
# Good — hierarchical naming
action="research.web_search"
action="research.data_analysis"
action="communication.email_send"

# Bad — vague names
action="step1"
action="do_thing"
```

### 2. Resource Scoping

Scope policies to specific resources:

```python
@GovernedNode(
    citadel_client=client,
    action="db.query",
    resource="db:customers",  # Policy can differ per table
)
async def query_customers(state):
    ...
```

### 3. Approval Gates

Force human approval for sensitive operations:

```python
@GovernedNode(
    citadel_client=client,
    action="payment.process",
    requires_approval=True,  # Always requires human sign-off
)
async def process_payment(state):
    ...
```

## Example: Multi-Agent Research

```python
from langgraph.graph import StateGraph
from citadel.integrations.langgraph import GovernedNode, GovernedStateGraph

class ResearchState(AgentState):
    query: str
    results: list
    confidence: float
    approved: bool

# Web search agent
@GovernedNode(client, action="research.search")
async def search(state: ResearchState):
    return {"results": await web_search(state.query)}

# Analysis agent
@GovernedNode(client, action="research.analyze")
async def analyze(state: ResearchState):
    confidence = await analyze_results(state.results)
    return {"confidence": confidence}

# Report agent (requires approval)
@GovernedNode(client, action="report.generate", requires_approval=True)
async def generate_report(state: ResearchState):
    report = await create_report(state.results)
    return {"report": report}

# Build graph
graph = GovernedStateGraph(client, ResearchState)
graph.add_node("search", search)
graph.add_node("analyze", analyze)
graph.add_node("report", generate_report)
graph.add_edge("search", "analyze")
graph.add_conditional_edges(
    "analyze",
    lambda s: "report" if s["confidence"] > 0.8 else "search",
    {"report": "report", "search": "search"},
)

app = graph.compile()
```

## Error Handling

```python
from citadel.core.sdk import ActionBlocked, ApprovalRequired

try:
    result = await app.ainvoke({"query": "..."})
except ActionBlocked:
    # Policy blocked — handle gracefully
    await fallback_strategy()
except ApprovalRequired as e:
    # Human approval needed
    await notify_approver(e.approval_id)
```

## Compliance & Audit

Every node execution is logged:
- Node name and action
- Input state (sanitized)
- Policy decision
- Execution time
- Audit hash for verification

## See Also

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Citadel Policies](../core-concepts/policies.md)
- [K2.6 Integration](kimi-k26.md)
