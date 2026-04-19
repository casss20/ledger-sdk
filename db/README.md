# Ledger Database Architecture

Control-system database design for AI governance. Optimized for deterministic decisions, auditability, and policy enforcement.

## Two Logical Stores

```
┌─────────────────────────────────────────────────────────┐
│              OPERATIONAL STORE (Postgres)              │
│  • Active policies      • Capability tokens            │
│  • Kill switches        • Approval state                 │
│  • Actor registry       • Rate limit metadata          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              AUDIT/EVENT STORE (Postgres)              │
│  • Every action attempt   • Decision path               │
│  • Execution results      • Approval outcomes           │
│  • Integrity chain        • Hash-chained events         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              EPHEMERAL CACHE (Redis)                   │
│  • Rate limit counters  • Distributed locks             │
│  • Hot kill switch cache • Approval queue fanout        │
└─────────────────────────────────────────────────────────┘
```

**Golden rule:** Postgres is the source of truth. Redis is for speed only.

## Design Principles

### 1. Append-Only Where Possible
**Never overwrite history:**
- `audit_events` — hash-chained, immutable
- `policy_snapshots` — resolved policy at decision time
- `decisions` — terminal outcome, one per action
- `actions` — canonical request record

**Why replay matters:** Every decision must be reproducible with original action payload, policy version, and capability state.

### 2. Mutable Only for Live State
**These tables change:**
- `capabilities` — use count decrements
- `kill_switches` — enabled/disabled toggles
- `approvals` — status transitions (pending → approved/rejected)
- `actors` — status updates (active/suspended/revoked)

### 3. Separate Normalized Action from Audit Trail
| Table | Purpose | Use Case |
|-------|---------|----------|
| `actions` | Clean canonical request | "What was requested?" |
| `audit_events` | Full chronological story | "What happened during processing?" |
| `decisions` | Terminal outcome | "What was the final verdict?" |

### 4. Every Decision Replayable
Stored for replay:
- `actions.payload_json` — original request
- `decisions.policy_snapshot_id` — policy version used
- `decisions.capability_token` — capability that authorized
- `decisions.context_json` — ambient state at decision time

## Main Tables

### Operational Store

| Table | Purpose | Mutability |
|-------|---------|------------|
| `actors` | Who can act | Status mutable |
| `policies` | Policy definitions | Status mutable (lifecycle) |
| `policy_snapshots` | Resolved immutable snapshots | Append-only |
| `capabilities` | Token-based permissions | Use count mutable |
| `kill_switches` | Emergency controls | Enabled mutable |
| `approvals` | Human-in-the-loop queue | Status mutable |

### Audit/Event Store

| Table | Purpose | Mutability |
|-------|---------|------------|
| `actions` | Canonical action request | Append-only |
| `decisions` | Terminal decision per action | Append-only |
| `audit_events` | Full chronological history | Append-only, hash-chained |

## Redis Usage

### ✅ Good for Redis (ephemeral)
```
ratelimit:{actor}:{action}      → Sliding window counters
lock:capability:{token}         → Atomic capability use
lock:approval:{id}              → Approval decision lock
cache:killswitch:{scope}        → Hot kill switch (TTL: 5s)
cache:policy:{tenant}:{scope}   → Cached policy (TTL: 30s)
approvals:pending               → Queue fanout for pub/sub
dedupe:{key}                    → Idempotency (TTL: 5m)
```

### ❌ Never in Redis (Postgres truth)
- Audit log
- Policy definitions
- Final approval state
- Capability authoritative state
- Decision history

## Data Flow Example

```
Agent calls: stripe.charge
│
├─ 1. Store in `actions` (canonical request)
├─ 2. Resolve `policy_snapshots` (which policy applies)
├─ 3. Check `kill_switches` (emergency stop?)
├─ 4. Check `capabilities` (have permission?)
│   └─ Redis lock for atomic decrement
├─ 5. Assess risk → may create `approvals` entry
├─ 6. Write `decisions` (blocked/allowed/pending)
├─ 7. Append `audit_events` (every step logged)
│
└─ 8. If approved → execute → log result
```

## Quick Start

```bash
# Create database
createdb ledger_control

# Run schema
psql ledger_control -f db/schema.sql

# Verify integrity function
psql ledger_control -c "SELECT * FROM verify_audit_chain();"

# Test capability consumption
psql ledger_control -c "SELECT * FROM consume_capability('cap_xxx', 'actor_1');"
```

## Helper Functions

| Function | Purpose |
|----------|---------|
| `verify_audit_chain()` | Check hash chain integrity |
| `consume_capability(token, actor)` | Atomic capability use |
| `set_updated_at()` | Auto-update timestamp trigger |
| `prevent_policy_mutation()` | Enforce policy immutability |
| `forbid_audit_mutation()` | Block audit updates/deletes |

## Idempotency Strategy

```sql
-- Unique constraint prevents duplicates
INSERT INTO actions (actor_id, action_name, idempotency_key, ...)
VALUES ('agent_1', 'email.send', 'req_123', ...)
ON CONFLICT (actor_id, idempotency_key) DO NOTHING;

-- Redis hot cache (5m TTL)
SETEX dedupe:req_123 300 "1"
```

## Production Checklist

- [ ] WAL archiving for audit immutability
- [ ] Object-store replication for long-term retention
- [ ] Table partitioning on `audit_events` by `event_ts`
- [ ] Remove foreign keys for ultra-hot paths (optional)
- [ ] Monitor JSONB index overhead
- [ ] Set up `pending_approvals_queue` alerts
- [ ] Configure Redis for ephemeral cache only

## Schema Evolution

**Immutable tables** (append-only):
- `actions`, `decisions`, `audit_events`, `policy_snapshots`
- Add new columns only, never modify existing

**Mutable tables** (live state):
- `capabilities`, `kill_switches`, `approvals`, `actors`, `policies` (status only)
- Normal migration patterns apply