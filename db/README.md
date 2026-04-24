# CITADEL Database Architecture

Control-system database design for AI governance. Optimized for deterministic decisions, auditability, and policy enforcement.

## Two Logical Stores

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              OPERATIONAL STORE (Postgres)              â”‚
â”‚  â€¢ Active policies      â€¢ Capability tokens            â”‚
â”‚  â€¢ Kill switches        â€¢ Approval state                 â”‚
â”‚  â€¢ Actor registry       â€¢ Rate limit metadata          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                          â”‚
                          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              AUDIT/EVENT STORE (Postgres)              â”‚
â”‚  â€¢ Every action attempt   â€¢ Decision path               â”‚
â”‚  â€¢ Execution results      â€¢ Approval outcomes           â”‚
â”‚  â€¢ Integrity chain        â€¢ Hash-chained events         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                          â”‚
                          â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              EPHEMERAL CACHE (Redis)                   â”‚
â”‚  â€¢ Rate limit counters  â€¢ Distributed locks             â”‚
â”‚  â€¢ Hot kill switch cache â€¢ Approval queue fanout        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Golden rule:** Postgres is the source of truth. Redis is for speed only.

## Design Principles

### 1. Append-Only Where Possible
**Never overwrite history:**
- `audit_events` â€” hash-chained, immutable
- `policy_snapshots` â€” resolved policy at decision time
- `decisions` â€” terminal outcome, one per action
- `actions` â€” canonical request record

**Why replay matters:** Every decision must be reproducible with original action payload, policy version, and capability state.

### 2. Mutable Only for Live State
**These tables change:**
- `capabilities` â€” use count decrements
- `kill_switches` â€” enabled/disabled toggles
- `approvals` â€” status transitions (pending â†’ approved/rejected)
- `actors` â€” status updates (active/suspended/revoked)

### 3. Separate Normalized Action from Audit Trail
| Table | Purpose | Use Case |
|-------|---------|----------|
| `actions` | Clean canonical request | "What was requested?" |
| `audit_events` | Full chronological story | "What happened during processing?" |
| `decisions` | Terminal outcome | "What was the final verdict?" |

### 4. Every Decision Replayable
Stored for replay:
- `actions.payload_json` â€” original request
- `decisions.policy_snapshot_id` â€” policy version used
- `decisions.capability_token` â€” capability that authorized
- `decisions.context_json` â€” ambient state at decision time

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

### âœ… Good for Redis (ephemeral)
```
ratelimit:{actor}:{action}      â†’ Sliding window counters
lock:capability:{token}         â†’ Atomic capability use
lock:approval:{id}              â†’ Approval decision lock
cache:killswitch:{scope}        â†’ Hot kill switch (TTL: 5s)
cache:policy:{tenant}:{scope}   â†’ Cached policy (TTL: 30s)
approvals:pending               â†’ Queue fanout for pub/sub
dedupe:{key}                    â†’ Idempotency (TTL: 5m)
```

### âŒ Never in Redis (Postgres truth)
- Audit log
- Policy definitions
- Final approval state
- Capability authoritative state
- Decision history

## Data Flow Example

```
Agent calls: stripe.charge
â”‚
â”œâ”€ 1. Store in `actions` (canonical request)
â”œâ”€ 2. Resolve `policy_snapshots` (which policy applies)
â”œâ”€ 3. Check `kill_switches` (emergency stop?)
â”œâ”€ 4. Check `capabilities` (have permission?)
â”‚   â””â”€ Redis lock for atomic decrement
â”œâ”€ 5. Assess risk â†’ may create `approvals` entry
â”œâ”€ 6. Write `decisions` (blocked/allowed/pending)
â”œâ”€ 7. Append `audit_events` (every step logged)
â”‚
â””â”€ 8. If approved â†’ execute â†’ log result
```

## Quick Start

```bash
# Create database
createdb citadel_control

# Run schema
psql citadel_control -f db/schema.sql

# Verify integrity function
psql citadel_control -c "SELECT * FROM verify_audit_chain();"

# Test capability consumption
psql citadel_control -c "SELECT * FROM consume_capability('cap_xxx', 'actor_1');"
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