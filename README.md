# Ledger SDK

**AI Governance: Constitution + Audit for Agent Builders**

Stop agent accidents before they happen. Block risky actions, require human approval, log everything to tamper-proof audit trails, and kill features instantly.

```python
from ledger.sdk import Ledger

gov = Ledger(audit_dsn="postgresql://...", agent="my-agent")

@gov.governed(action="send_email", resource="outbound_email", flag="email_send")
async def send_email(to: str, subject: str, body: str):
    # Blocked until approved
    return await smtp.send(to, subject, body)
```

## Features

- 🛡️ **@governed decorator** — Wrap any function with risk classification
- 🛑 **Kill switches** — Instantly disable features without deploy
- ✅ **Approval queue** — Human-in-the-loop for risky actions
- 📊 **Audit trail** — Hash-chained, tamper-evident logging to Postgres
- 📜 **Constitution** — Markdown governance rules LLMs read
- ⚡ **FastAPI integration** — Drop-in middleware and routes

## Quick Start

```bash
pip install ledger-sdk
```

```python
import asyncio
from ledger.sdk import Ledger

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

## Documentation

- [Integration Guide](docs/GOVERNANCE_WIRING.md) — How to wire into your app
- [Product Roadmap](docs/ROADMAP.md) — 4-week plan to production
- [API Reference](https://github.com/casss20/ledger-sdk/tree/master/src/ledger)

## Examples

```bash
# Run the governed actions demo
python examples/governed_actions.py

# FastAPI integration
python examples/fastapi_integration.py
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

## Why Ledger?

| Competitors | Ledger |
|-------------|--------|
| "AI governance platform" (vague) | "Stop agent accidents" (concrete) |
| Days of integration | 4 lines of code |
| $2k+/mo | $0 open source |

**Customer reaction**: *"Oh fuck, we NEED this. Our agent nearly broke production yesterday."*

## License

MIT — See [LICENSE](LICENSE)

---

Built for [agent-world](https://github.com/casss20/agent-world) | [GitHub](https://github.com/casss20/ledger-sdk)
