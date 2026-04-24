# Architectural Decision Record: Governor vs SDK

**Date:** 2026-04-19  
**Status:** DECIDED - Option B (Keep Separation)  
**Decision Maker:** Anthony + Agent

---

## The Decision

**Option B: Keep separation of concerns**

- **Citadel SDK** (`sdk.py`): Owns execution â€” the `@governed` decorator, capability tokens, kill switches
- **Governor**: Owns visibility â€” tracks all action lifecycle, provides query API, dashboard data
- **Boundary**: CITADEL reports to Governor; Governor never controls execution

---

## Why Not Option A (Governor Absorbs CITADEL)

| Concern | Option A | Option B (Chosen) |
|---------|----------|-------------------|
| **Complexity** | Governor becomes "god object" | Clear, separated responsibilities |
| **Testing** | Hard to mock Governor for unit tests | CITADEL testable without Governor |
| **Coupling** | Tight coupling â€” can't use CITADEL without Governor | Loose coupling â€” Governor is optional for visibility |
| **Single Responsibility** | Violates SRP | Clean: CITADEL acts, Governor observes |
| **What We Built** | Requires major refactor | Current integration is correct |

---

## Why Option B Is Right

1. **It matches what we just built** â€” CITADEL already reports state transitions to Governor cleanly
2. **Error handling fits naturally** â€” CITADEL catches exceptions, reports `FAILED` to Governor
3. **Subgraph execution is simple** â€” CITADEL manages flow; Governor tracks which subgraph ran
4. **Dashboard stays simple** â€” Governor is read-only data source, no execution logic

---

## Implementation Rules

### Governor does NOT:
- Call `@governed` decorators
- Issue capability tokens
- Check kill switches
- Make approval decisions

### Governor DOES:
- Receive state transitions from CITADEL
- Store complete action lifecycle
- Answer queries about pending/failed/skipped actions
- Provide summary statistics for dashboard

### CITADEL does NOT:
- Query Governor during execution (fire-and-forget reporting)
- Wait for Governor approval
- Check Governor state before acting

### CITADEL DOES:
- Create records in Governor at start
- Transition states during execution
- Report final state (SUCCESS/FAILED/DENIED/TIMEOUT/SKIPPED)

---

## Unblocked Work

Now that decision is made, these can be implemented:

1. **Error handling** (`try_governed`, `@catch`) â€” CITADEL catches, reports to Governor
2. **Subgraph execution** â€” CITADEL manages flow, Governor tracks subgraph state
3. **Unified dashboard** â€” Governor provides all data, read-only

---

## Code Pattern

```python
# CITADEL executes
gov = CITADEL(...)

@gov.governed(action="send_email")
async def send_email(to: str, subject: str, body: str):
    # CITADEL reports to Governor internally
    return await smtp.send(to, subject, body)

# Governor is queried elsewhere (dashboard, monitoring)
from CITADEL import get_governor
governor = get_governor()

# Read-only queries
pending = governor.list_pending()
failed = governor.list_failed()
summary = governor.get_summary()
```

---

**Signed:** 2026-04-19  
**Next Action:** Implement error handling with `@try_governed` and `@catch`
