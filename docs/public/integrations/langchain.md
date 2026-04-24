# LangChain Integration

## What you'll learn

- Install CITADEL's LangChain callback handler
- Govern every tool call in your LangChain agent
- Configure policies for specific LangChain tools
- View LangChain agent actions in the dashboard
- Handle policy denials gracefully in agent chains

---

## Installation

```bash
pip install citadel-sdk[langchain]
# or
pip install citadel-sdk langchain langchain-openai
```

---

## Basic Integration

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from citadel_sdk.integrations.langchain import CITADELCallbackHandler

# Initialize CITADEL
import citadel_sdk
CITADEL = citadel_sdk.Client(api_key="ldk_test_...")

# Create the callback handler
citadel_handler = CITADELCallbackHandler(
    client=CITADEL,
    agent_id="langchain-agent-01",
    namespace="customer-support"
)

# Build your agent
llm = ChatOpenAI(model="gpt-4")
tools = [search_tool, calculator_tool, email_tool]
agent = create_openai_functions_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[citadel_handler]
)

# Run with automatic governance
result = agent_executor.invoke({
    "input": "Find user 123's order and send them a shipping update"
})
```

---

## How It Works

The `CITADELCallbackHandler` hooks into LangChain's callback system:

```
Agent decides to use tool
    â†“
LangChain calls tool
    â†“
CITADELCallbackHandler intercepts
    â†“
CITADEL evaluates against policies
    â†“
    â”œâ”€ ALLOWED â†’ Execute tool, return result
    â”œâ”€ DENIED â†’ Return error to agent
    â””â”€ APPROVAL_REQUIRED â†’ Return approval URL
```

---

## Tool-Specific Policies

### Govern search tool
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: search-limit
spec:
  trigger:
    action: search_tool.run
  enforcement:
    type: rate_limit
    limit: 10
    window: 1m
```

### Govern email tool
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: email-approval
spec:
  trigger:
    action: email_tool.run
    condition: params.to not_in ["@company.com"]
  enforcement:
    type: require_approval
    approvers: [compliance@company.com]
```

### Govern calculator (allow)
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: calculator-allow
spec:
  trigger:
    action: calculator_tool.run
  enforcement:
    type: allow
```

---

## Handling Denials

When a tool call is denied, the agent receives an error. Handle it in your agent logic:

```python
from langchain_core.exceptions import OutputParserException

class GovernedAgentExecutor(AgentExecutor):
    def _handle_tool_error(self, error):
        if "PolicyDeniedError" in str(error):
            return "I cannot perform this action due to governance policy. Let me try an alternative."
        return super()._handle_tool_error(error)
```

---

## Custom Agent Types

### ReAct agents
```python
from langchain.agents import initialize_agent, AgentType

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.REACT_DOCSTORE,
    callbacks=[citadel_handler]
)
```

### Plan-and-execute
```python
from langchain_experimental.plan_and_execute import PlanAndExecute

agent = PlanAndExecute(
    planner=planner,
    executor=executor,
    callbacks=[citadel_handler]
)
```

---

## Multi-Agent Chains

Govern chains where agents call other agents:

```python
# Parent agent
parent_handler = CITADELCallbackHandler(
    client=CITADEL,
    agent_id="parent-agent",
    trace_context=parent_trace
)

# Child agent inherits trace context
child_handler = CITADELCallbackHandler(
    client=CITADEL,
    agent_id="child-agent",
    trace_context=parent_trace  # Links to parent
)
```

---

## Troubleshooting

### "Callback not firing"
Ensure you're passing `callbacks=[citadel_handler]` to the executor, not the agent:
```python
# Correct
AgentExecutor(agent=agent, tools=tools, callbacks=[citadel_handler])

# Incorrect
AgentExecutor(agent=agent, tools=tools)  # Missing callbacks
```

### "Policy denied but agent retries"
Add retry logic with exponential backoff:
```python
from langchain_core.runnables import RunnableRetry

agent_with_retry = RunnableRetry(
    bound=agent_executor,
    retry_exception_types=(PolicyDeniedError,),
    max_attempts=3
)
```

---

## Next steps

- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
- [Recipe: Email Sending Rate Limit](../recipes/email-sending-rate-limit.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
