# LEDGER SDK

**AI governance infrastructure for agent builders.**

Two-layer model:
- **Soft layer** — markdown files loaded into the LLM's system prompt (values, runtime rules, identity)
- **Hard layer** — Python enforcement (capability tokens, hash-chained audit, kill switches, rate limits)

Soft = what's *wise*. Hard = what's *allowed*. Together = governance.

## Quick Start

```python
from ledger.sdk import Ledger, Denied

async def main():
    gov = Ledger(
        audit_dsn="postgres://postgres:password@localhost/postgres",
        agent="nova",
    )
    await gov.start()
    
    # Register approval hook for high-risk actions
    gov.set_approval_hook(lambda ctx: True)  # Replace with real approval logic
    
    # Govern a function
    @gov.governed(action="send_message", resource="email", flag="email_send")
    async def send_email(to, body):
        return {"to": to, "sent": True}
    
    # Execute with full audit trail
    result = await send_email("user@x.com", "hello")
    
    # Kill switch blocks immediately
    gov.killsw.kill("email_send", reason="phishing incident")
    
    try:
        await send_email("user@x.com", "again")
    except Denied:
        print("Blocked by kill switch")
    
    # Verify audit chain integrity
    ok, count = await gov.audit.verify_integrity()
    print(f"Audit OK: {ok}, entries: {count}")
    
    await gov.stop()

asyncio.run(main())
```

See `examples/basic.py` for full working example.

## Architecture

```
┌─────────────────────────────────────┐
│ SOFT LAYER (markdown → LLM context) │
│ Reasoning, judgment, values         │
├─────────────────────────────────────┤
│ HARD LAYER (Python enforcement)     │
│ Capability tokens, audit, killswitch│
└─────────────────────────────────────┘
```

### Runtime Paths

| Path | Use Case | Files Loaded |
|------|----------|--------------|
| `fast` | Quick queries | CONSTITUTION, IDENTITY |
| `standard` | General tasks | + EXECUTOR |
| `structured` | Complex work | + PLANNER, CRITIC, FOCUS |
| `high_risk` | Destructive/irreversible | + GOVERNOR, ALIGNMENT, FAILURE |

## Governance Features

- **Capability tokens** — scoped, time-bound, max-use action tokens
- **Hash-chained audit** — SHA-256 chained log, tamper-evident
- **Kill switches** — instant disable of any feature
- **Risk classification** — LOW/MEDIUM/HIGH with NONE/SOFT/HARD approval
- **Approval hooks** — human-in-the-loop for high-risk actions

## Requirements

- Python 3.11+
- Postgres 14+ (for audit log)
- asyncpg

## Installation

```bash
pip install -e .
```

## Running Tests

```bash
# Requires Postgres running locally
export AUDIT_DSN="postgres://postgres:password@localhost/postgres"
pytest
```

Skip audit tests if no Postgres available:
```bash
pytest -k "not audit"
```

## License

MIT