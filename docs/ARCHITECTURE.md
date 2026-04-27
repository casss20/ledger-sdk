# Citadel: AI Governance Architecture

## Positioning Statement

**Citadel is AI governance infrastructure for production AI systems.**

Its kernel is runtime enforcement, so governance is not just observed — it is enforced.

---

## The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE INTELLIGENCE                   │
│     (Alignment, Planning, Adaptation, Focus, Learning)      │
├─────────────────────────────────────────────────────────────┤
│                    GOVERNANCE FRAMEWORK                      │
│     (Policy, Identity, Approvals, Lifecycle, Versioning)    │
├─────────────────────────────────────────────────────────────┤
│                    GOVERNANCE KERNEL                         │
│     (Enforcement, Deterministic Policy, Audit, Kill)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Governance Kernel (Enforcement)

**Purpose:** The non-negotiable core where governance becomes real.

**Rule:** Without this layer, governance is documentation. With this layer, governance has teeth.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Governor** | `core/governor.py` | Strategic oversight, intervention, escalation levels 0-3 |
| **Executor** | `core/executor.py` | Execution momentum, capability enforcement, mode switching |
| **Runtime** | `core/runtime.py` | Activation cycle, path selection (Fast/Standard/Structured/High-risk) |
| **Capability** | `governance/capability.py` | Token-based capability issuance and consumption |
| **Risk** | `governance/risk.py` | Risk classification (SOFT/HARD approvals) |
| **Audit** | `governance/audit.py` | Hash-chained immutable decision log |
| **KillSwitch** | `governance/killswitch.py` | Emergency stop, fail-closed behavior |
| **Constitution** | `core/constitution.py` | Behavioral constraints beyond risk (identity, disclosure, safety) |

### Enforcement Points

- Action interception at the boundary
- Deterministic policy evaluation
- Capability checks (token-based)
- Rate limiting
- Fail-closed on error

---

## Layer 2: Governance Framework (Policy Structure)

**Purpose:** How decisions are structured over time.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Identity** | `identity.py` | Agent registry, status tracking, lifecycle |
| **Alignment** | `governance/alignment.py` | Loyalty protocol, challenge system, initiative boundaries |
| **Durable Approval** | `governance/durable.py` | Async approval queues, promises, human-in-the-loop |
| **Rate Limit** | `governance/rate_limit.py` | Token bucket rate limiting, burst control |

### Framework Features

- Policy hierarchy (Constitution → World → User Request)
- Role/actor boundaries
- Escalation rules (Level 0-3)
- Human oversight hooks
- Policy versioning (SELF-MOD.md pattern)
- Lifecycle management

---

## Layer 3: Governance Intelligence (Behavioral)

**Purpose:** Long-term edge through learning and adaptation.

**Rule:** This is not fluff if tied back to actual decisioning.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Planner** | `ops/planner.py` | Structured planning, milestones, risk assessment before execution |
| **Critic** | `governance/critic.py` | Quality review, contradiction detection, 5-dimension validation |
| **Focus** | `system/focus.py` | Anti-distraction, scope protection, deep work enforcement |
| **Adaptation** | `ops/adaptation.py` | Behavioral adjustment based on patterns (conservative) |
| **After Action** | `governance/after_action.py` | Learning loop, reflection, pattern extraction |
| **Prune** | `governance/prune.py` | Context cleanup, noise removal, signal preservation |
| **Opportunity** | `ops/opportunity.py` | Leverage detection, skill gaps, automation candidates |
| **Failure** | `ops/failure.py` | Recovery protocol, rollback, escalation |

### Intelligence Features

- Alignment checking (long-term vs short-term conflict)
- Quality validation before output
- Behavioral adaptation (after 3+ observations)
- Pattern learning and application
- Opportunity surfacing
- Failure recovery

---

## The Three Product Surfaces

Citadel exposes three surfaces to users:

### Surface 1: Governance Controls
**What policy exists?**

```python
from citadel import Constitution, Governor, Alignment

# Define behavioral constraints
constitution = Constitution([
    "Never impersonate a human",
    "Always disclose when acting as AI",
    "Respect user privacy"
])

# Configure governance
gov = Governor(
    escalation_levels=True,
    kill_switch=True,
    constitution=constitution
)

# Set alignment boundaries
alignment = Alignment(
    initiative_level=InitiativeLevel.GUIDED,
    world_goals={"primary": "build_saas"}
)
```

**Features:**
- Allowed/forbidden actions
- Approval workflows (SOFT/HARD)
- Escalation rules (0-3)
- Least privilege enforcement
- Kill switches
- Constitutional constraints

---

### Surface 2: Governance Enforcement
**How policy is applied in real time.**

```python
from citadel import Citadel, ExecutionMode

citadel = Citadel(audit_dsn="postgresql://...")

# Runtime enforcement at action boundary
@citadel.governed(action="send_email", resource="outbound")
async def send_email(to: str, body: str):
    return await smtp.send(to, body)

# Mode switching based on risk
citadel.set_mode(ExecutionMode.STRICT)  # High-risk scenario
```

**Features:**
- Action interception
- Deterministic policy evaluation (< 10ms)
- Capability token checks
- Rate limiting enforcement
- Fail-closed behavior
- Real-time risk scoring

---

### Surface 3: Governance Evidence
**How you prove it worked.**

```python
from citadel import AuditService, AfterAction

# Every decision logged with hash chain
audit = AuditService(dsn="postgresql://...")
event_hash = await audit.log(
    actor="agent_nova",
    action="send_email",
    resource="outbound",
    risk="medium",
    approved=True
)

# Verify integrity
valid, count = await audit.verify_integrity()

# Structured reflection
report = after_action.reflect(
    context=context,
    execution_details=details
)
```

**Features:**
- Immutable audit chain
- Decision traceability
- Policy version tracking
- Approval history
- Tamper-proof logging
- Compliance reporting

---

## Governance = Runtime + Framework + Intelligence

### The Correct Definition

> **AI governance is the system of controls, permissions, decision policies, oversight, and evidence that determines what an AI system is allowed to do, under what conditions, and with what accountability.**

This includes:
- **Prevention** (controls block bad actions)
- **Oversight** (approvals, escalation, human review)
- **Accountability** (audit trail, evidence)
- **Lifecycle control** (policy versioning, adaptation)

### The Wrong Definitions (What We Avoid)

- ❌ "Monitoring" — too passive, no enforcement
- ❌ "Guardrails" — too vague, not systematic
- ❌ "Runtime blocking only" — too narrow, misses framework
- ❌ "Policy theater" — documentation without enforcement

---

## Trust-Aware Decision Flow

Citadel's decision flow integrates trust scores and trust bands before policy evaluation:

```
Agent requests action
    ↓
Kill Switch Check (first gate — always)
    ↓
Trust Evaluation:
    - Compute or retrieve trust snapshot
    - Determine trust band (REVOKED / PROBATION / STANDARD / TRUSTED / HIGHLY_TRUSTED)
    - Determine constraints (approval, spend, rate limit, blocked actions)
    - Check probation status (overrides band if active)
    - Check circuit breaker (stages REVOKED if score < 0.15)
    ↓
Policy Evaluation (receives trust context)
    - Policy rules evaluated with trust band in context
    - Trust can ADD approval requirements
    - Trust can reduce spend/rate limits
    - Trust CANNOT remove a policy DENY
    ↓
Decision Recorded (with trust_snapshot_id for replay)
    ↓
Token Issued (gt_cap_) or Action Executed
```

### Trust band approval matrix

| Action | REVOKED | PROBATION | STANDARD | TRUSTED | HIGHLY_TRUSTED |
|--------|---------|-----------|----------|---------|----------------|
| **execute** | blocked | allowed + introspection | allowed | allowed | allowed |
| **delegate** | blocked | blocked | allowed | allowed | allowed |
| **handoff** | blocked | blocked | approval | allowed | allowed |
| **gather** | blocked | blocked | approval | allowed | allowed |
| **destroy** | blocked | blocked | approval | approval | approval |
| **revoke** | blocked | blocked | approval | approval | allowed |

**Key rules:**
1. Kill switch is checked first — trust never bypasses emergency stop
2. Trust can only ADD constraints (approval, lower limits) — never remove
3. Even HIGHLY_TRUSTED requires approval for `destroy` — no band bypasses destructive action controls
4. Every decision stores `trust_snapshot_id` for deterministic replay

### Trust score computation

Trust scores are deterministic 0.00-1.00 values computed from 9 weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Identity verification | 0.25 | Cryptographic identity verification status |
| Health score | 0.20 | Agent operational health (0-100) |
| Identity age | 0.15 max | Days since creation (0.5% per day, capped at 30d) |
| Compliance record | 0.15 | Policy violations in last 7 days |
| Quarantine status | 0.10 | Major penalty (-0.30) if quarantined |
| Action rate | 0.10 | Daily action volume (suspicious if >1000) |
| Budget adherence | 0.05 | Token spend vs budget ratio |
| Challenge reliability | 0.05 | Pass rate on cryptographic challenges |
| Score trend | 0.03 | Rapid score change bonus/penalty |

**Score boundaries:**
- REVOKED: 0.00–0.19
- PROBATION: 0.20–0.39
- STANDARD: 0.40–0.59
- TRUSTED: 0.60–0.79
- HIGHLY_TRUSTED: 0.80–1.00

---

## Trust Architecture

Citadel's trust model adds deterministic behavioral signals to the governance kernel without replacing policy authority.

### Five Trust Bands

| Band | Score Range | Meaning |
|------|-------------|---------|
| **REVOKED** | 0.00 – 0.19 | Identity disabled. Emergency state. |
| **PROBATION** | 0.20 – 0.39 | Strict monitoring. New or low-trust agents. |
| **STANDARD** | 0.40 – 0.59 | Normal operation. Default for established agents. |
| **TRUSTED** | 0.60 – 0.79 | Elevated privileges. Demonstrated reliability. |
| **HIGHLY_TRUSTED** | 0.80 – 1.00 | Full privileges. Long history of reliability. |

### Trust-Aware Decision Flow

```
Agent requests action
    ↓
Kill Switch Check (first gate — trust never bypasses)
    ↓
Trust Evaluation → Band, Score, Constraints
    ↓
Policy Evaluation → ALLOW / DENY / REQUIRE_APPROVAL
    ↓
Merge Trust Constraints → May add approval, reduce quota
    ↓
Decision Recorded (with trust_snapshot_id for replay)
    ↓
Token Issued / Action Executed
```

### Key Principles

1. **Kill switch is always first** — trust never bypasses emergency stop
2. **Trust can only ADD constraints** — it cannot remove a policy denial
3. **Every decision stores `trust_snapshot_id`** — deterministic replay for audit
4. **Probation overrides band** — `probation_until` > now means PROBATION regardless of score
5. **Even HIGHLY_TRUSTED needs approval for `destroy`** — no band bypasses destructive action controls

### Trust Score Components

| Factor | Weight | Description |
|--------|--------|-------------|
| Identity verification | 0.25 | Cryptographic identity verification |
| Health score | 0.20 | Agent operational health |
| Identity age | 0.15 | Days since creation (capped at 30d) |
| Compliance record | 0.15 | Policy violations in last 7 days |
| Quarantine status | 0.10 | Major penalty if quarantined |
| Action rate | 0.10 | Daily action volume |
| Budget adherence | 0.05 | Token spend vs budget ratio |
| Challenge reliability | 0.05 | Pass rate on cryptographic challenges |
| Score trend | 0.03 | Rapid score change bonus/penalty |

### Trust Policy Integration

Trust bands influence policy enforcement through the `TrustPolicyEngine`:

```python
from citadel import TrustPolicyEngine, TrustBand

engine = TrustPolicyEngine()
result = engine.evaluate(
    action="database.write",
    trust_snapshot=snapshot
)
# result.decision: allow | require_approval | deny
# result.constraints: { max_spend, rate_limit, approval_required_for }
```

### Trust Audit Events

Every trust change is recorded:

| Event Type | When |
|---|---|
| `TRUST_BAND_CHANGED` | Band changes |
| `TRUST_SCORE_COMPUTED` | Every computation |
| `TRUST_PROBATION_STARTED` | Probation begins |
| `TRUST_PROBATION_ENDED` | Probation expires |
| `TRUST_OVERRIDE` | Operator sets band |
| `TRUST_CIRCUIT_BREAKER` | Emergency drop |
| `TRUST_KILL_SWITCH_DROP` | Kill switch → REVOKED |

### Resources

- [Trust Architecture Guide](docs/public/guides/trust-architecture.md) — Deep-dive documentation
- [Trust Scoring](docs/public/core-concepts/trust-scoring.md) — Core concepts
- [Trust Scoring API](docs/public/core-concepts/trust-scoring.md) — Score computation and factors

---

## Technical Spine: Runtime as Kernel

### Why Runtime is Non-Negotiable

```
Without Runtime:
├─ Policy exists in documents
├─ Violations are logged
├─ Humans review after the fact
└─ Governance = observation

With Runtime:
├─ Policy is code
├─ Violations are blocked
├─ Approvals happen before execution
└─ Governance = enforcement
```

### Runtime Enforcement Points

```
Agent → Action Request
        ↓
   [GOVERNOR] ← Escalation check
        ↓
   [CONSTITUTION] ← Behavioral rules
        ↓
   [ALIGNMENT] ← Long-term goal check
        ↓
   [RISK] ← Classification (SOFT/HARD)
        ↓
   [CAPABILITY] ← Token issuance
        ↓
   [EXECUTOR] ← Execution with monitoring
        ↓
   [AUDIT] ← Immutable log
```

---

## Decision-First Runtime Authorization

Citadel's hardened runtime model separates durable decision truth from short-lived execution proof.

```
Agent requests sensitive action
        |
        v
Policy and approval state evaluated
        |
        v
Governance decision persisted first
        |
        v
Short-lived gt_cap_ token issued
        |
        v
Runtime gateway introspects token
        |
        v
Expiry, revocation, scope, workspace, and kill-switch state checked
        |
        v
Action executes only when active=true
        |
        v
Outcome links back to token -> decision_id -> policy_version -> approval_state
```

The decision record is the source of truth. The `gt_cap_` token is a scoped runtime artifact that proves an allowed decision exists, but it is not the root of authority. This lets Citadel revoke a token, revoke a decision, or activate emergency kill-switch state and have the next protected operation fail introspection even if the token has not expired yet.

This preserves the control-plane model:

- `decision_id` is the audit spine.
- `trace_id` links runtime outcome evidence across systems.
- `policy_version` and `approval_state` survive the execution chain.
- Kill switches are central state, not best-effort client behavior.

---

## Code Organization by Layer

```
citadel/
├── core/                    # GOVERNANCE KERNEL
│   ├── governor.py          # Strategic oversight
│   ├── executor.py          # Execution enforcement
│   ├── runtime.py           # Activation cycle
│   └── constitution.py      # Behavioral constraints
│
├── governance/              # KERNEL + FRAMEWORK + INTELLIGENCE
│   ├── capability.py        # Kernel: tokens
│   ├── risk.py              # Kernel: classification
│   ├── audit.py             # Kernel + Evidence: logging
│   ├── killswitch.py        # Kernel: emergency stop
│   ├── rate_limit.py        # Framework: throttling
│   ├── durable.py           # Framework: approvals
│   ├── alignment.py         # Framework: loyalty
│   ├── critic.py            # Intelligence: quality
│   ├── prune.py             # Intelligence: cleanup
│   └── after_action.py      # Intelligence: learning
│
├── ops/                     # INTELLIGENCE
│   ├── planner.py           # Structured planning
│   ├── failure.py           # Recovery protocol
│   ├── adaptation.py        # Behavioral adjustment
│   └── opportunity.py       # Leverage detection
│
└── system/                  # INTELLIGENCE
    └── focus.py             # Anti-distraction
```

---

## Competitive Differentiation

### Competitors (Credo, Arthur, Lakera, etc.)

```
Approach: Build controls one by one
Month 1: Framework
Month 2: Email control
Month 3: DB control
Month 4-18: Add more controls individually

Result: 18+ months to full platform
         $2M+ engineering cost
         28 months to 50 controls
```

### Citadel

```
Approach: Governance architecture first
Month 1: Kernel + framework + intelligence
Month 2-12: Policy packs (1 week per tool)

Result: 6 months to full platform
         $500k engineering cost
         50+ controls in production

Advantage: 36 MD files = governance rules written
           New tool = policy pack + wire
           Same engine, different rules
```

---

## Implementation Status

### ✅ Complete (Production Ready)

**Kernel:**
- [x] Governor (escalation, intervention)
- [x] Executor (execution, modes)
- [x] Runtime (activation, paths)
- [x] Constitution (behavioral rules)
- [x] Capability (tokens)
- [x] Risk (classification)
- [x] Audit (hash-chained logs)
- [x] KillSwitch (emergency stop)
- [x] **Trust Model** (score, bands, probation, circuit breaker)

**Framework:**
- [x] Identity (registry, lifecycle)
- [x] Alignment (loyalty, challenges)
- [x] Durable Approvals (async queues)
- [x] Rate Limiting (token bucket)
- [x] **Trust Policy Engine** (deterministic band-based constraints)

**Intelligence:**
- [x] Planner (structured planning)
- [x] Critic (quality review)
- [x] Focus (anti-distraction)
- [x] Adaptation (behavioral tuning)
- [x] After Action (learning loop)
- [x] Prune (context cleanup)
- [x] Opportunity (leverage detection)
- [x] Failure (recovery protocol)

**Trust Architecture:**
- [x] 5-band trust model (REVOKED, PROBATION, STANDARD, TRUSTED, HIGHLY_TRUSTED)
- [x] Deterministic score computation (9 weighted factors)
- [x] Append-only trust snapshots with full audit replay
- [x] Policy integration (trust-aware constraints)
- [x] Circuit breaker with staging
- [x] Probation with automatic escalation
- [x] Operator override with dual approval
- [x] Kill switch → trust interaction (automatic REVOKED on score collapse)

### ⏳ Pending (Defined in MD files)

- [ ] HEARTBEAT (system health polling)
- [ ] SELF-MOD (policy evolution)
- [ ] START (boot orchestration)
- [ ] WORLD (goal hierarchy)
- [ ] USER (relationship model)
- [ ] MEMORY (context management)

---

## Usage: Full Stack Example

```python
from citadel import (
    # Kernel
    Citadel, Governor, Constitution, ExecutionMode,
    # Framework
    Alignment, InitiativeLevel,
    # Intelligence
    Planner, Critic, Focus
)

# 1. Configure Governance (Controls)
constitution = Constitution([
    "Never impersonate a human",
    "Always disclose when acting as AI"
])

gov = Governor(
    constitution=constitution,
    kill_switch_enabled=True
)

# 2. Set Alignment (Framework)
alignment = Alignment(
    world_goals={"primary": "build_saas"},
    initiative_level=InitiativeLevel.GUIDED
)

# 3. Create Citadel (Enforcement Surface)
citadel = Citadel(
    audit_dsn="postgresql://localhost/citadel",
    governor=gov,
    constitution=constitution
)

# 4. Define Governed Action
@citadel.governed(action="deploy", resource="production")
async def deploy_to_production(image: str):
    # Runtime enforcement happens here:
    # - Governor checks escalation level
    # - Constitution validates behavior
    # - Risk classification (likely HARD approval)
    # - Capability token issued
    # - Execution monitored
    # - Audit log written
    return await k8s.deploy(image)

# 5. Planning (Intelligence)
planner = Planner()
plan = planner.create_plan(
    PlanningContext(
        task_description="Deploy production",
        estimated_steps=5,
        stakes="high",
        is_irreversible=True
    )
)

# 6. Quality Review (Intelligence)
critic = Critic()
report = critic.review(
    output=deploy_result,
    dimensions=[ReviewDimension.SAFETY, ReviewDimension.COMPLETENESS]
)

# 7. Focus Protection (Intelligence)
focus = Focus()
focus.enter_focus(
    task_id="deploy-123",
    description="Deploy to production",
    protected=True  # Deep work mode
)

# Distractions will be deflected
```

---

## Summary

Citadel is **AI governance infrastructure** with three layers:

1. **Kernel** — Runtime enforcement (has teeth)
2. **Framework** — Policy structure (scales)
3. **Intelligence** — Behavioral learning (improves)

This gives you:
- Big company category (AI governance)
- Concrete technical spine (runtime enforcement)
- Competitive moat (36 governance rules already written)
- Fast expansion (1 week per new tool)

**Positioning:**
> Citadel defines, enforces, and proves what AI systems are allowed to do.

**Technical:**
> At its core, Citadel uses runtime enforcement to make governance actionable at the execution boundary.
