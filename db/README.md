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

# Verify integrity function works
psql ledger_control -c "SELECT * FROM verify_audit_chain();"
```

## Views for Common Queries

### Active Governance State
```sql
SELECT * FROM active_governance_state;
-- Shows all actors, policies, kill switches currently active
```

### Pending Approvals Queue
```sql
SELECT * FROM pending_approvals_queue;
-- Human-in-the-loop items needing review
```

### Decision Replay Log
```sql
SELECT * FROM decision_replay_log 
WHERE action_id = 'xxx';
-- Full context for reproducing a decision
```

## Minimal MVP

Start with just these tables:
1. `actions` — what was requested
2. `decisions` — what was decided
3. `policies` — current policy set
4. `approvals` — human review queue
5. `audit_events` — what happened
6. `kill_switches` — emergency stops

Add later:
7. `capabilities` — fine-grained permissions
8. `actors` — full registry
9. `policy_snapshots` — full replay support

## Tech Stack Recommendation

| Layer | Tool | Role |
|-------|------|------|
| Primary store | Postgres 15+ | All authoritative data |
| Ephemeral cache | Redis 7+ | Rate limits, locks, hot cache |
| Access | asyncpg / SQLAlchemy | Python async |
| Schema | JSONB early, normalize later | Flexible rules, strict core |

## Why This Design

**Not a generic app database** — optimized for:
- Deterministic policy decisions (<10ms evaluation)
- Tamper-proof audit chains (hash verification)
- Fast replay for debugging (snapshot references)
- Horizontal scaling (stateless decision engine)
- Compliance (immutable history, integrity proofs)

**Control-system DNA:** Every design choice supports governance enforcement at the action boundary.
