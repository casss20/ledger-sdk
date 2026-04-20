# Ledger Kernel Guarantees

> Internal contract for the Ledger governance kernel.
> Version: v0.1.0-kernel-green
> Last updated: 2026-04-21

## What Ledger Guarantees

### 1. Deterministic Decision Paths
Every action processed by the kernel follows the **exact same precedence chain**:

```
Kill Switch → Capability → Policy → Approval → Execution
```

No action can bypass an earlier stage. No policy can override a kill switch.

### 2. Terminal States (One Per Action)
Every action reaches exactly **one** terminal state:

| Status | Meaning | Persistence |
|--------|---------|-------------|
| `BLOCKED_SCHEMA` | Failed schema/validation | action + decision + audit |
| `BLOCKED_EMERGENCY` | Kill switch active | action + decision + audit |
| `BLOCKED_CAPABILITY` | Missing/invalid capability | action + decision + audit |
| `BLOCKED_POLICY` | Policy rule blocked | action + decision + audit |
| `RATE_LIMITED` | Rate limit exceeded | action + decision + audit |
| `PENDING_APPROVAL` | Waiting for human review | action + decision + approval + audit |
| `REJECTED_APPROVAL` | Human rejected | action + decision + approval + audit |
| `EXPIRED_APPROVAL` | Approval window expired | action + decision + approval + audit |
| `ALLOWED` | Approved (pre-execution) | action + decision + audit |
| `EXECUTED` | Successfully executed | action + decision + execution_result + audit |
| `FAILED_EXECUTION` | Execution error | action + decision + execution_result + audit |
| `FAILED_AUDIT` | Audit logging failed | action only (best effort) |

### 3. Idempotency
Submitting the same `(actor_id, idempotency_key)` twice returns the **cached decision** without:
- Inserting a duplicate action
- Re-executing the action
- Creating duplicate audit events (logs reference original action)

### 4. Audit Chain Integrity
All audit events are:
- **Append-only**: No updates or deletes permitted (trigger-enforced)
- **Hash-chained**: Each event's `prev_hash` links to the previous event's `event_hash`
- **Verifiable**: `SELECT * FROM verify_audit_chain()` returns chain validity

### 5. Immutable Snapshots
Policy snapshots are immutable. Once created, a snapshot's hash never changes. This enables **deterministic replay** of any decision.

### 6. Capability Atomicity
Capability use counting is atomic. Concurrent requests for the same capability cannot exceed `max_uses`.

---

## What Ledger Does NOT Guarantee

### 1. Execution Safety
Ledger guarantees the **decision** to execute, not the **outcome** of execution. A `FAILED_EXECUTION` means the governed function threw — Ledger does not recover the function's side effects.

### 2. Real-time Kill Switch
Kill switches are checked at action entry, not continuously. A kill switch activated *after* an action enters the kernel does not affect in-flight actions.

### 3. Network Partition Tolerance
Ledger requires database connectivity. During a partition:
- Actions cannot be submitted
- Pending approvals cannot be resolved
- Audit events cannot be written

Ledger **fails closed**: no decision without DB confirmation.

### 4. Byzantine Actors
Ledger assumes actors are who they claim (via `actor_id`). It does not authenticate requests — that is the responsibility of the upstream gateway.

### 5. Clock Synchronization
Capability expiry and approval deadlines rely on database `NOW()`. Clock skew between application servers and Postgres can cause off-by-seconds behavior.

---

## Precedence Order (Hardcoded)

```python
# 1. Kill Switch (highest precedence)
if kill_switch.active:
    return BLOCKED_EMERGENCY

# 2. Capability (if token provided)
if capability_token and not cap.valid:
    return BLOCKED_CAPABILITY

# 3. Policy evaluation
if policy.effect == "BLOCK":
    return BLOCKED_POLICY
if policy.effect == "PENDING_APPROVAL":
    # Continue to approval service (do not block here)
    pass

# 4. Approval check
if approval.required:
    return PENDING_APPROVAL

# 5. Execute (lowest precedence)
return EXECUTED or FAILED_EXECUTION
```

**Rule**: Earlier stages cannot be overridden by later stages. A kill switch blocks regardless of policy or approval state.

---

## Conformance Suite

The following scenarios are tested and guaranteed:

| Test | Scenario | Expected |
|------|----------|----------|
| test_01 | Kill switch active | BLOCKED_EMERGENCY |
| test_02 | Policy blocks | BLOCKED_POLICY |
| test_03 | Expired capability | BLOCKED_CAPABILITY |
| test_04 | Approval required | PENDING_APPROVAL |
| test_05 | Approval rejected | REJECTED_APPROVAL |
| test_06 | Approval expired | EXPIRED_APPROVAL |
| test_07 | Allowed + executed | EXECUTED |
| test_08 | Execution failure | FAILED_EXECUTION |
| test_09 | Duplicate idempotency | Cached decision |
| test_10 | Audit chain | Hash chain valid |

---

## Next Hardening Targets

- [ ] Concurrency: Racing capability consumption
- [ ] Concurrency: Duplicate idempotency submissions
- [ ] Concurrency: Approval state changes mid-flight
- [ ] Concurrency: Parallel audit writes under load
- [ ] Concurrency: Kill switch toggled during execution

---

*This document is frozen at v0.1.0-kernel-green. Changes require review.*
