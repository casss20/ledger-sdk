# Ledger SDK

**AI Governance: Constitution + Audit for Agent Builders**

Stop agent accidents before they happen. Block risky actions, require human approval, log everything to tamper-proof audit trails, and kill features instantly.

[![PyPI version](https://badge.fury.io/py/ledger-sdk.svg)](https://pypi.org/project/ledger-sdk/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```python
from ledger import Ledger, Retry, try_governed

gov = Ledger(audit_dsn="postgresql://...", agent="my-agent")

@try_governed(Retry(times=3))  # Auto-retry on failure
@gov.governed(action="send_email", resource="outbound_email", flag="email_send")
async def send_email(to: str, subject: str, body: str):
    # Blocked until approved, retried on failure, tracked in audit
    return await smtp.send(to, subject, body)
```

## Features

- 🛡️ **@governed decorator** — Wrap any function with risk classification
- 🔄 **Error handling** — `Retry()`, `Catch()`, `Default()`, `DeadLetter()`
- 🎯 **Subgraph execution** — Run only the outputs you need
- 📈 **Analytics** — Detect "50 emails in 1 minute" anomalies
- 🛑 **Kill switches** — Instantly disable features without deploy
- ✅ **Approval queue** — Human-in-the-loop for risky actions
- 📊 **Audit trail** — Hash-chained, tamper-evident logging
- 📜 **Constitution** — Markdown governance rules LLMs read
- ⚡ **FastAPI integration** — Drop-in middleware and routes

## Installation

```bash
# Core functionality
pip install ledger-sdk

# With optional dependencies
pip install ledger-sdk[fastapi]    # FastAPI integration
pip install ledger-sdk[durable]    # Redis-backed execution
pip install ledger-sdk[sidecar]    # HTTP sidecar pattern
pip install ledger-sdk[all]        # Everything
```

## Quick Start

### Basic Governance

```python
import asyncio
from ledger import Ledger

async def main():
    gov = Ledger(audit_dsn="postgresql://user:pass@localhost/db")
    await gov.start()
    
    @gov.governed(action="publish", resource="listing")
    async def publish_listing(data: dict):
        return {"status": "published"}
    
    # This will block for approval
    result = await publish_listing({"title": "New Product"})
    print(result)
    
    await gov.stop()

asyncio.run(main())
```

### Error Handling

```python
from ledger import try_governed, Retry, Catch

# Auto-retry with exponential backoff
@try_governed(Retry(times=3, backoff=2.0))
@gov.governed(action="stripe_charge")
async def charge_customer(amount: float):
    return await stripe.charges.create(amount=amount)

# Route failures to fallback
@try_governed(Catch(notify_admin_alert))
@gov.governed(action="send_email")
async def send_critical_alert(message: str):
    return await smtp.send(to="admin@company.com", body=message)
```

### Subgraph Execution

```python
from ledger import SubgraphExecutor, get_subgraph_executor

executor = get_subgraph_executor()

@executor.output("summary", cost_estimate=0.05)
@gov.governed(action="generate_summary")
async def generate_summary(text: str):
    return await llm.summarize(text)

@executor.output("translation", cost_estimate=0.08)
@gov.governed(action="translate_text")
async def translate_text(text: str):
    return await llm.translate(text, lang="es")

# Run just what you need
result = await executor.run_output("summary", text="Long document...")
```

### Analytics & Monitoring

```python
from ledger import get_analytics, get_profiler

# Check for anomalies
analytics = get_analytics()
metrics = await analytics.analyze_window(TimeWindow.last_hour())

# Build behavior profile
profiler = get_profiler()
profile = await profiler.build_profile(agent="my-agent", days=7)

# Health check
health = await analytics.check_agent_health("my-agent")
print(f"Health score: {health['health_score']}/100")
```

## Dashboard API

```python
from ledger import get_fastapi_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(get_fastapi_router())

# Endpoints:
# GET /dashboard/summary       → Executive summary
# GET /dashboard/pending       → Pending approvals
# GET /dashboard/failed        → Recent failures
# GET /dashboard/anomalies     → Detected anomalies
# GET /dashboard/agent/{agent}/health → Per-agent health
```

## Documentation

- [Integration Guide](docs/GOVERNANCE_WIRING.md) — How to wire into your app
- [Product Roadmap](docs/ROADMAP.md) — 4-week plan to production
- [Architecture Decision](docs/ARCHITECTURE_DECISION.md) — Governor vs SDK design
- [API Reference](https://github.com/casss20/ledger-sdk/tree/master/src/ledger)

## Examples

```bash
# Run the governed actions demo
python examples/governed_actions.py

# FastAPI integration
python examples/fastapi_integration.py

# Error handling patterns
python examples/error_handling_demo.py
```

## Governance Constitution

The SDK ships with 24 governance markdown files:

- `CONSTITUTION.md` — Core principles and approval rules
- `GOVERNOR.md` — Escalation patterns
- `RUNTIME.md` — Mode selection (fast/standard/structured/high_risk)
- `EXECUTOR.md` — Execution patterns
- `AUDIT.md` — Audit requirements
- ...and 19 more

These are injected into LLM system prompts so agents *know* the rules.

## Weft-Inspired Patterns

Ledger SDK adopts proven patterns from [Weft](https://github.com/WeaveMindAI/weft):

| Pattern | Implementation |
|---------|----------------|
| Durable execution | Redis-backed promises (`DurablePromise`) |
| Null propagation | `SkipExecution` cascades through graphs |
| Recursive groups | Collapsible `ActionGroup`/`ActionNode` |
| Subgraph execution | `SubgraphExecutor` for selective output |
| Native mocking | `@mockable` decorator |
| Compile validation | Pydantic `validate_at_startup` |
| Dense syntax | `gov.action()`, `gov.email()` DSL |
| Sidecar pattern | HTTP bridge to infrastructure |

## Why Ledger?

| Competitors | Ledger |
|-------------|--------|
| "AI governance platform" (vague) | "Stop agent accidents" (concrete) |
| Days of integration | 4 lines of code |
| $2k+/mo | $0 open source |
| Black box | Full visibility (Governor, Analytics, Dashboard) |

**Customer reaction**: *"Oh fuck, we NEED this. Our agent nearly broke production yesterday."*

## Changelog

### v0.1.0 (2026-04-19)

- Initial release
- Core governance: `@governed`, kill switches, approval queue, audit
- Error handling: `Retry`, `Catch`, `Default`, `DeadLetter`
- Subgraph execution: selective output execution
- Cross-action analytics: anomaly detection, health scoring
- Dashboard API: FastAPI endpoints
- 8 Weft patterns adopted

## License

MIT — See [LICENSE](LICENSE)

---

Built for [agent-world](https://github.com/casss20/agent-world) | [GitHub](https://github.com/casss20/ledger-sdk) | [PyPI](https://pypi.org/project/ledger-sdk/)
