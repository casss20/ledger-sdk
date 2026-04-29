# Citadel Trust Architecture

> **Schema Path: C (Hybrid)** — Minimal identity metadata + Separate historical snapshots
> **Policy Model: Governance Signal with Deterministic Bands**

---

## 1. Recommendation

**IMPLEMENT NOW — with caution.**

Citadel should adopt a **hybrid trust model**:

- **Identity metadata** (`verification_status`, `compliance_tags`) stays on `agent_identities` — human-speed changes
- **Behavioral state** (`health_score`, `actions_today`, `quarantined`) stays on `agents` — operational metrics
- **Trust assessments** live in `actor_trust_snapshots` — append-only, time-bounded, fully auditable

This replaces the current opaque `metadata JSONB` overwrite with an explicit, reproducible, history-preserving system.

---

## 2. Why This Design

### Trust is a Behavioral Signal, Not an Identity Attribute

Identity is **who you are** (slowly changing, credential-linked). Trust is **what the system concluded about your behavior** at a specific time. Conflating them creates an opaque system where an operator cannot explain why an agent's trust dropped.

### Trust Needs History

Every trust score change must be explainable. The current system overwrites `metadata JSONB` in place. The new system creates a new row for every computation, preserving:
- Previous scores
- Factor breakdowns
- Raw inputs
- Triggering events
- Operator overrides

### Trust Changes Frequently

Behavioral metrics change on every action. Computing trust on every request would make the policy engine non-deterministic. Instead:
- **Batch computation** every 15 minutes (cron job)
- **Event-triggered** recomputation on quarantine, kill switch, or violation
- **Hot path** reads the latest snapshot (indexed, <1ms)

### Trust Must Be Versioned

The `actor_trust_snapshots` table references `policy_version_at_compute`. When a decision is made, it stores `trust_snapshot_id`. This means:
- "Decision D was evaluated using trust snapshot T at time X"
- Full replay capability for audit

### Trust Must Be Separated for Performance

The `agents.trust_band` column is a **denormalized cache** of the latest snapshot's band. The hot path reads this single column, not the snapshot table. The cache is updated asynchronously by the trust computation job.

---

## 3. Schema Plan

### New Table: `actor_trust_snapshots`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `snapshot_id` | UUID | PK, gen_random_uuid() | Unique identifier for this assessment |
| `actor_id` | TEXT | NOT NULL, FK→actors | Which actor this assessment is for |
| `computed_at` | TIMESTAMPTZ | NOT NULL | When this snapshot was computed |
| `valid_from` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When this snapshot becomes valid |
| `valid_until` | TIMESTAMPTZ | NULL = currently active | When this snapshot was superseded |
| `score` | DECIMAL(5,4) | CHECK [0.0, 1.0] | Computed trust score |
| `band` | TEXT | CHECK in enum | Trust band: REVOKED, PROBATION, STANDARD, TRUSTED, HIGHLY_TRUSTED |
| `probation_until` | TIMESTAMPTZ | NULL | If set and > now, actor is in probation |
| `probation_reason` | TEXT | | Why probation was applied |
| `factors` | JSONB | NOT NULL, DEFAULT '{}' | Score factor breakdown (explainability) |
| `raw_inputs` | JSONB | NOT NULL, DEFAULT '{}' | Raw data that produced this score |
| `computation_method` | TEXT | CHECK in ('batch', 'event', 'override') | How this snapshot was computed |
| `triggering_event` | TEXT | | What event caused recomputation |
| `triggering_event_id` | TEXT | | ID of the triggering audit event |
| `operator_id` | TEXT | NULL | Human operator who manually set this |
| `operator_reason` | TEXT | | Explanation for manual override |
| `policy_version_at_compute` | TEXT | | Policy version active when computed |
| `tenant_id` | TEXT | | Tenant isolation |
| `supersedes_snapshot_id` | UUID | FK→self | Previous snapshot this one replaced |
| `superseded_reason` | TEXT | | Why the previous snapshot was replaced |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Row creation time |

### Modified Table: `decisions`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `trust_snapshot_id` | UUID | NULL, FK→actor_trust_snapshots | Trust snapshot active at decision time |

### Modified Table: `agents`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `trust_band` | TEXT | NULL, CHECK in enum | Denormalized cache of current band |
| `probation_until` | TIMESTAMPTZ | NULL | Active probation deadline |

### Indexes

```sql
-- Hot path: current snapshot lookup
CREATE INDEX idx_trust_snapshots_actor_current
    ON actor_trust_snapshots (actor_id, computed_at DESC)
    WHERE valid_until IS NULL;

-- History: full timeline
CREATE INDEX idx_trust_snapshots_actor_timeline
    ON actor_trust_snapshots (actor_id, computed_at DESC);

-- Tenant-scoped queries
CREATE INDEX idx_trust_snapshots_tenant_band
    ON actor_trust_snapshots (tenant_id, band, computed_at DESC)
    WHERE valid_until IS NULL;

-- Time-based cleanup
CREATE INDEX idx_trust_snapshots_computed_at
    ON actor_trust_snapshots (computed_at DESC);

-- Unique: one current snapshot per actor
CREATE UNIQUE INDEX idx_trust_snapshots_actor_current_unique
    ON actor_trust_snapshots (actor_id) WHERE valid_until IS NULL;
```

---

## 4. Migration Plan

### Phase 1: Schema Deployment (Additive Only)

1. **Create `actor_trust_snapshots` table** — New table, zero impact on existing data
2. **Add nullable `trust_snapshot_id` to `decisions`** — No rewrite, no constraint
3. **Add nullable `trust_band` to `agents`** — No rewrite, no constraint
4. **Add nullable `probation_until` to `agents`** — No rewrite, no constraint
5. **Create indexes** — `CREATE INDEX` (not `CREATE INDEX CONCURRENTLY` in migration, but note for production)
6. **Add RLS policies** — Tenant isolation for new table
7. **Add helper function** `get_actor_trust_snapshot()` — Stable function for policy queries

**Rollback:** Drop new table + nullable columns = instant. No data loss.

### Phase 2: Backfill (After Deployment)

```sql
-- Batch backfill: compute STANDARD snapshots for all existing agents
INSERT INTO actor_trust_snapshots (
    actor_id, tenant_id, score, band, factors, raw_inputs,
    computation_method, valid_from
)
SELECT
    a.agent_id,
    a.tenant_id,
    0.50,
    'STANDARD',
    '{}',
    '{"backfill": true}',
    'batch',
    NOW()
FROM agents a
WHERE a.agent_id NOT IN (
    SELECT actor_id FROM actor_trust_snapshots WHERE valid_until IS NULL
)
LIMIT 1000;

-- Update cache
UPDATE agents a
SET trust_band = (
    SELECT band FROM actor_trust_snapshots ts
    WHERE ts.actor_id = a.agent_id AND ts.valid_until IS NULL
    ORDER BY computed_at DESC LIMIT 1
)
WHERE trust_band IS NULL;
```

**Safety:** Process in batches of 1000. No single large transaction. Can be interrupted and resumed.

### Phase 3: Application Code Rollout

1. Deploy new `TrustSnapshotEngine`, `TrustPolicyEngine`, `TrustAuditLogger`
2. Old `TrustScorer` API delegates to new engine (backward compatible)
3. DecisionEngine optionally integrates trust (if `trust_policy_engine` configured)
4. Dashboard reads from `actor_trust_snapshots` for history, `agents.trust_band` for current state

### Phase 4: Deprecation (Future Release)

- Remove `trust_score`/`trust_level` from `agent_identities` (currently deprecated but kept for backward compat)
- Remove old `TrustScorer` class (after all callers migrate)

---

## 5. Runtime Impact

### Reading Trust Data

**Hot path (policy evaluation):**
```python
# Fast: reads denormalized cache
SELECT trust_band, probation_until FROM agents WHERE agent_id = $1

# Fallback: reads latest snapshot if cache is stale
SELECT * FROM actor_trust_snapshots
WHERE actor_id = $1 AND valid_until IS NULL
ORDER BY computed_at DESC LIMIT 1
```

**History query:**
```python
# Full timeline
SELECT * FROM actor_trust_snapshots
WHERE actor_id = $1 ORDER BY computed_at DESC
```

### Writing Trust Data

```python
# Compute and store (batch job)
engine = TrustSnapshotEngine(db_pool)
score = await engine.compute_and_store(
    agent_id="agent-1",
    tenant_id="tenant-1",
    computation_method="batch",
)

# Operator override
score = await engine.operator_override(
    agent_id="agent-1",
    tenant_id="tenant-1",
    operator_id="op-123",
    target_band=TrustBand.REVOKED,
    reason="Emergency stop",
)
```

### Decision Engine Integration

```python
# DecisionEngine now accepts optional trust_policy_engine
decision_engine = DecisionEngine(
    policy_backend=opa_backend,
    audit_logger=audit,
    kill_switch=ks,
    trust_policy_engine=trust_engine,  # Optional
)

# Trust context is added to policy evaluation
# Trust can ADD constraints (approval, rate limit reduction)
# Trust NEVER removes constraints or overrides policy
```

### Backward Compatibility

- Old `TrustScorer` API works unchanged (delegates to `TrustSnapshotEngine`)
- Old `agent_identities.trust_score` column still readable (deprecated)
- Application code can run against old schema during rollout (trust engine is optional)
- No hard dependency on trust data before backfill completes

---

## 6. Policy Impact

### What Trust Changes

| Band | Approval | Spend | Rate Limit | Actions Blocked | Introspection |
|---|---|---|---|---|---|
| **REVOKED** | All blocked | 0% | 0% | execute, delegate, handoff, gather | N/A |
| **PROBATION** | delegate, handoff, gather, destroy | 50% | 50% | delegate, handoff | execute |
| **STANDARD** | destroy, revoke | 100% | 100% | — | destroy |
| **TRUSTED** | destroy | 150% | 200% | — | destroy |
| **HIGHLY_TRUSTED** | destroy only | 200% | 500% | — | destroy |

### What Trust Does NOT Change

- **Kill switch** — Always checked FIRST. Trust never bypasses emergency stop.
- **Lineage** — Parent/child scope narrowing is structural, not trust-based.
- **Entitlements** — Quota/budget from commercial system are separate from behavioral trust.
- **Token validity** — Cryptographic token validation is independent of trust band.
- **RLS** — Database row-level security is independent of trust.

### Trust as Policy Context

```json
{
  "trust_band": "STANDARD",
  "trust_score": 0.55,
  "trust_snapshot_id": "snap-123",
  "trust_probation_active": false,
  "trust_constraints": {
    "require_approval_for": ["destroy", "revoke"],
    "approval_bypass_for_risk_below": "low",
    "max_spend_multiplier": 1.0,
    "rate_limit_multiplier": 1.0
  }
}
```

Policy rules can reference `trust_band` in conditions. The policy engine evaluates these conditions deterministically.

---

## 7. Policy Bands

### REVOKED (0.00 – 0.19)

**Meaning:** Identity disabled. Emergency state.

**Triggers:**
- Kill switch activation
- Operator manual override
- Score drops below 0.20
- Circuit breaker fires

**Actions:**
- All actions: **BLOCKED**
- No token issuance
- No delegation
- No handoff

**Exit:** Operator manual restore to PROBATION.

---

### PROBATION (0.20 – 0.39)

**Meaning:** New or low-trust agent under strict monitoring.

**Entry:**
- New agent (default for 7 days)
- Score drops from STANDARD
- Restored from REVOKED

**Actions:**
- execute: **Allowed with introspection required**
- delegate, handoff, gather: **BLOCKED**
- destroy, revoke: **BLOCKED**
- protected_tool_use: **Requires approval**

**Quotas:** 50% of normal

**Exit:**
- Minimum 3 days in probation
- Score >= 0.40 for 48 hours
- Operator manual approval

**Extension:**
- Score drops below 0.25
- Policy violation during probation
- Kill switch triggered

---

### STANDARD (0.40 – 0.59)

**Meaning:** Normal operation. Default for established agents.

**Actions:**
- execute: **Allowed**
- delegate: **Allowed**
- handoff, gather: **Requires approval**
- destroy, revoke: **Requires approval**
- kill_switch_trigger: **Requires approval**

**Quotas:** 100% (normal)

---

### TRUSTED (0.60 – 0.79)

**Meaning:** Elevated privileges. Demonstrated reliable behavior.

**Actions:**
- execute, delegate, handoff, gather: **Allowed**
- destroy, revoke: **Requires approval**
- kill_switch_trigger: **Allowed**

**Quotas:** 150% spend, 200% rate limit

**Audit:** Enhanced logging (INFO level)

---

### HIGHLY_TRUSTED (0.80 – 1.00)

**Meaning:** Full privileges. Long history of reliable behavior.

**Actions:**
- execute, delegate, handoff, gather: **Allowed**
- destroy: **Requires approval** (never bypassed)
- revoke: **Allowed**
- kill_switch_trigger: **Allowed**

**Quotas:** 200% spend, 500% rate limit

**Kill Switch:** Still applies. No exceptions.

---

## 8. Trust Inputs

### Signals That Affect Trust

| Signal | Affects Score | Affects Band | Visible in Audit |
|---|---|---|---|
| Identity verified | Yes (0.25 weight) | Yes | Yes |
| Identity age | Yes (0.15 max) | Yes | Yes |
| Health score | Yes (0.20 weight) | Yes | Yes |
| Quarantine status | Yes (-0.30 penalty) | Yes | Yes |
| Action rate | Yes (+/- 0.10) | Yes | Yes |
| Compliance violations | Yes (+/- 0.15) | Yes | Yes |
| Token budget adherence | Yes (+/- 0.05) | Yes | Yes |
| Challenge reliability | Yes (+/- 0.05) | Yes | Yes |
| Score trend | Yes (+/- 0.03) | Yes | Yes |
| Human operator override | N/A (direct band set) | Yes | Yes (HIGH severity) |
| Kill switch activation | N/A (direct REVOKED) | Yes | Yes (CRITICAL severity) |

### Signal Processing

- **Batch computation** (cron): Recomputes all scores every 15 minutes
- **Event-triggered** (immediate): Recomputes on quarantine, kill switch, violation
- **Override** (immediate): Operator manually sets band, bypasses score

---

## 9. Determinism and Explainability

### Same Inputs → Same Band → Same Decision

The score computation is **fully deterministic**:
- No randomness
- No ML models
- No external API calls
- All weights are code-level constants

```python
# Identical raw inputs always produce identical score
score, factors = engine._compute_score(raw_inputs)
# score is always the same for the same raw_inputs
# factors explain every component
```

### Replay Capability

Every decision stores `trust_snapshot_id`. To replay:
```sql
SELECT snapshot_json FROM actor_trust_snapshots
WHERE snapshot_id = 'snap-123';
```

This gives the exact trust context that was active at decision time.

### No Hidden Logic

- All thresholds are in `trust_bands.py` (code-level constants)
- All weights are in `TRUST_FACTOR_WEIGHTS` (asserted to sum to 1.0)
- All band constraints are in `BAND_CONSTRAINTS` (frozen dataclass)
- No configuration files, no environment variables, no runtime tuning

---

## 10. Probation and Escalation

### New Agent Probation Flow

```
Agent Created
    └── PROBATION (default, 7 days)
          ├── Score < 0.25 → Extend probation (+7 days)
          ├── Violation → Extend probation (+7 days)
          ├── Kill switch → REVOKED
          ├── Operator override → STANDARD (if approved)
          └── Score >= 0.40 for 48h + min 3 days → STANDARD
```

### Circuit Breaker

```
Score drops below 0.15
    └── STAGE: Prepare REVOKED transition
          ├── If score stays < 0.15 for 5 minutes → REVOKE
          └── If score recovers → Cancel staging
```

### Escalation Reversibility

| Transition | Reversible | How |
|---|---|---|
| STANDARD → PROBATION | Yes | Score improves + operator approval |
| TRUSTED → STANDARD | Yes | Score improves automatically |
| PROBATION → REVOKED | No (requires operator restore) | Manual operator action |
| Any → REVOKED | No | Manual operator restore to PROBATION |

---

## 11. Quota and Entitlements

### What Trust May Affect

- **max_spend multiplier**: Can reduce (PROBATION: 50%) or increase (TRUSTED: 150%)
- **rate_limit multiplier**: Can reduce or increase
- **approval requirements**: Can add (never remove)

### What Trust May NOT Affect

- **Base entitlements** from commercial plan — these are the floor
- **Hard quotas** set by operator — these are the ceiling
- **Billing** — trust is not a billing mechanism

### Example

```
Base entitlement: 1000 tokens/hour (from plan)
Trust multiplier: 1.5 (TRUSTED band)
Effective limit: 1500 tokens/hour

But if operator sets hard quota of 800:
Effective limit: 800 tokens/hour (hard quota wins)
```

---

## 12. Audit Model

### What Gets Written

| Event Type | When | Data |
|---|---|---|
| `TRUST_BAND_CHANGED` | Band changes | before/after band, score, snapshot_id, reason_code |
| `TRUST_SCORE_COMPUTED` | Every computation | score, band, snapshot_id, factors, raw_inputs |
| `TRUST_PROBATION_STARTED` | Probation begins | probation_until, reason |
| `TRUST_PROBATION_ENDED` | Probation expires | reason |
| `TRUST_PROBATION_EXTENDED` | Probation extended | new_until, reason |
| `TRUST_OVERRIDE` | Operator sets band | operator_id, from/to band, reason (HIGH severity) |
| `TRUST_CIRCUIT_BREAKER` | Emergency drop | from/to score/band, reason (CRITICAL severity) |
| `TRUST_KILL_SWITCH_DROP` | Kill switch → REVOKED | previous_band, kill_switch_reason |

### Audit Trail Query

```sql
-- Reconstruct why an agent's trust changed
SELECT
    event_type,
    action AS transition,
    metadata_json->>'reason_code' AS reason,
    metadata_json->>'from_band' AS from_band,
    metadata_json->>'to_band' AS to_band,
    created_at
FROM audit_events
WHERE target = 'agent-123'
  AND event_type LIKE 'TRUST_%'
ORDER BY created_at DESC;
```

---

## 13. Failure Modes

| Risk | Prevention |
|---|---|
| Score drops but band doesn't change | Band thresholds are checked on every computation. No caching. |
| Band changes but policy doesn't enforce | Policy engine reads latest snapshot at evaluation time. No stale cache. |
| Trust overrides kill switch | Kill switch is checked **before** trust evaluation. Impossible to bypass. |
| High trust grants too much power | Even HIGHLY_TRUSTED requires approval for `destroy`. Kill switch always applies. |
| New agent escapes probation early | Minimum 3-day probation + score threshold. Operator can extend. |
| Trust changes invisible | Every change writes to `audit_events` with full context. |
| Trust cached too long | `agents.trust_band` is a cache with SLA: updated within 15 min of computation. |
| Inconsistent behavior across workers | All workers read from same PostgreSQL table. No in-memory cache. |
| Schema mismatch during rollout | All new columns are NULLABLE. Application handles NULL gracefully. |
| Migration causes table rewrite | No NOT NULL columns with defaults on large tables. All new columns are nullable. |

---

## 14. Tests Required

### Schema Tests
- [x] `actor_trust_snapshots` table exists with correct columns
- [x] Indexes exist and are partial where specified
- [x] Unique constraint on `(actor_id) WHERE valid_until IS NULL`
- [x] RLS policies are enabled
- [x] `get_actor_trust_snapshot()` function works

### Migration Tests
- [x] Migration is additive (no existing data broken)
- [x] Nullable columns don't cause errors
- [x] Rollback: drop table + columns = clean

### Runtime Tests
- [x] Trust score computation is deterministic
- [x] Score-to-band mapping is correct for all ranges
- [x] Probation overrides band correctly
- [x] Trust constraints are applied to policy decisions
- [x] Trust never overrides kill switch
- [x] Backward compatibility with old TrustScorer API

### Policy Tests
- [x] Action matrix is correct for all bands
- [x] Band transitions follow rules
- [x] Circuit breaker fires at correct threshold
- [x] Operator override creates correct audit event
- [x] Quota multipliers are applied correctly

---

## 15. Risks / Tradeoffs

| Risk | Mitigation |
|---|---|
| **Storage growth** | Partition by `computed_at` month. Archive after 90 days. |
| **Score computation lag** | Event-triggered recomputation for critical events. |
| **Cache staleness** | `agents.trust_band` updated within 15 min. Dashboard reads snapshot table directly. |
| **Operator override abuse** | Require dual approval. 24h expiration unless renewed. HIGH severity audit. |
| **Probation duration** | Hard cap at 30 days. Operator must explicitly extend. |
| **Migration complexity** | All changes additive. Zero-downtime deployment. |

---

## 16. Final Recommendation

**IMPLEMENT WITH CAUTION.**

The trust architecture is ready for production. The migration is safe (all additive, nullable columns, no table rewrites). The policy engine integration is backward compatible. The audit trail is comprehensive.

**Recommended deployment order:**
1. Deploy migration 017 (schema changes)
2. Run backfill job (batch snapshots for existing agents)
3. Deploy application code (new trust engine, backward compatible)
4. Enable trust policy engine in DecisionEngine (optional, opt-in)
5. Update dashboard to read from snapshot table
6. Monitor for 1 week, then deprecate old `TrustScorer`

**Do not:**
- Skip the backfill phase
- Enable trust policy enforcement before backfill completes
- Change band thresholds without a policy version bump
- Use trust as a billing mechanism

**Do:**
- Monitor `audit_events` for unexpected trust transitions
- Review operator overrides weekly
- Archive old snapshots monthly
- Test rollback procedure before production deploy
