# Governance Wiring Guide

How to integrate Citadel SDK into your application.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  app.py startup                                 │
│  → start_governance()                           │
│  → LedgerEngine initialized                     │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  LLM System Prompt Construction                 │
│  → loads CONSTITUTION.md + governance layers      │
│  → injects into LLM context                     │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  @governed decorator (on tool calls)            │
│  → risk classification                          │
│  → capability token issuance                    │
│  → HARD approval gate if needed                 │
│  → audit log write                              │
│  → execute                                      │
└─────────────────────────────────────────────────┘
```

---

## Three Layers

### 1. Soft Governance (markdown → LLM)

The LLM reads constitutional rules from `citadel/core/*.md`:

- **CONSTITUTION.md** — Core principles, what requires approval
- **GOVERNOR.md** — Escalation patterns, when to involve humans
- **EXECUTOR.md** — Execution patterns, failure handling
- **RUNTIME.md** — Mode selection (fast/standard/structured/high_risk)

**Usage:**
```python
from citadel.sdk import Citadel

gov = Citadel(audit_dsn="...", agent="my-agent")
prompt = gov.build_prompt(task="Create a marketing campaign")
# Inject `prompt` into your LLM system message
```

### 2. Hard Governance (Python enforcement)

The `@governed` decorator wraps functions with:

- **Capability tokens** — scoped, time-bound, max-use
- **Risk classification** — LOW/MEDIUM/HIGH
- **Approval gates** — NONE/SOFT/HARD
- **Kill switches** — instant disable of features
- **Audit logging** — immutable, hash-chained

**Usage:**
```python
@gov.governed(action="publish", resource="campaign", flag="campaign_publish")
async def create_campaign(name: str, budget: float):
    return {"status": "created"}
```

### 3. Audit Trail

Every governed action is logged to Postgres:

- `actor` — who performed the action
- `action` — what was done
- `resource` — what was modified
- `risk` — low/medium/high
- `approved` — True/False
- `timestamp` — when
- `prev_hash` — hash chain for tamper detection

---

## FastAPI Integration

Copy `examples/fastapi_integration.py` to your project:

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from examples.fastapi_integration import start_governance, stop_governance

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_governance()
    yield
    await stop_governance()

app = FastAPI(lifespan=lifespan)
```

---

## Configuration

Environment variables:

```bash
# Required for audit logging
LEDGER_AUDIT_DSN=postgresql://user:pass@localhost/db

# Optional
LEDGER_LOG_LEVEL=INFO
```

---

## Running the Example

```bash
cd citadel-sdk

# Install
pip install -e ".[dev]"

# Start Postgres (optional, for full audit)
docker run -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres

# Run example
python examples/governed_actions.py
```

---

## Troubleshooting

**"citadel-sdk not installed"**
- Run `pip install -e .` from the citadel-sdk directory

**Audit log queries fail**
- Check `LEDGER_AUDIT_DSN` environment variable
- Verify Postgres is running

**Approval hook never called**
- Ensure you called `gov.set_approval_hook(your_hook)`
- Check that action is classified as `Approval.HARD`

**LLM not seeing constitution**
- Verify `citadel/core/CONSTITUTION.md` exists
- Check that `build_prompt()` returns content
