# Governance Wiring Guide

How to integrate Citadel SDK into your application.

---

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  app.py startup                                 â”‚
â”‚  â†’ start_governance()                           â”‚
â”‚  â†’ CITADELEngine initialized                     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”‚
               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  LLM System Prompt Construction                 â”‚
â”‚  â†’ loads CONSTITUTION.md + governance layers      â”‚
â”‚  â†’ injects into LLM context                     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
               â”‚
               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  @governed decorator (on tool calls)            â”‚
â”‚  â†’ risk classification                          â”‚
â”‚  â†’ capability token issuance                    â”‚
â”‚  â†’ HARD approval gate if needed                 â”‚
â”‚  â†’ audit log write                              â”‚
â”‚  â†’ execute                                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Three Layers

### 1. Soft Governance (markdown â†’ LLM)

The LLM reads constitutional rules from `CITADEL/core/*.md`:

- **CONSTITUTION.md** â€” Core principles, what requires approval
- **GOVERNOR.md** â€” Escalation patterns, when to involve humans
- **EXECUTOR.md** â€” Execution patterns, failure handling
- **RUNTIME.md** â€” Mode selection (fast/standard/structured/high_risk)

**Usage:**
```python
from CITADEL.sdk import CITADEL

gov = CITADEL(audit_dsn="...", agent="my-agent")
prompt = gov.build_prompt(task="Create a marketing campaign")
# Inject `prompt` into your LLM system message
```

### 2. Hard Governance (Python enforcement)

The `@governed` decorator wraps functions with:

- **Capability tokens** â€” scoped, time-bound, max-use
- **Risk classification** â€” LOW/MEDIUM/HIGH
- **Approval gates** â€” NONE/SOFT/HARD
- **Kill switches** â€” instant disable of features
- **Audit logging** â€” immutable, hash-chained

**Usage:**
```python
@gov.governed(action="publish", resource="campaign", flag="campaign_publish")
async def create_campaign(name: str, budget: float):
    return {"status": "created"}
```

### 3. Audit Trail

Every governed action is logged to Postgres:

- `actor` â€” who performed the action
- `action` â€” what was done
- `resource` â€” what was modified
- `risk` â€” low/medium/high
- `approved` â€” True/False
- `timestamp` â€” when
- `prev_hash` â€” hash chain for tamper detection

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
citadel_AUDIT_DSN=postgresql://user:pass@localhost/db

# Optional
citadel_LOG_LEVEL=INFO
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
- Check `citadel_AUDIT_DSN` environment variable
- Verify Postgres is running

**Approval hook never called**
- Ensure you called `gov.set_approval_hook(your_hook)`
- Check that action is classified as `Approval.HARD`

**LLM not seeing constitution**
- Verify `CITADEL/core/CONSTITUTION.md` exists
- Check that `build_prompt()` returns content
