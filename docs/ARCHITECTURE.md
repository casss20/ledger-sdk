# Ledger: AI Governance Architecture

## Positioning Statement

**Ledger is AI governance infrastructure for production AI systems.**

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

Ledger exposes three surfaces to users:

### Surface 1: Governance Controls
**What policy exists?**

```python
from ledger import Constitution, Governor, Alignment

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
from ledger import Ledger, ExecutionMode

ledger = Ledger(audit_dsn="postgresql://...")

# Runtime enforcement at action boundary
@ledger.governed(action="send_email", resource="outbound")
async def send_email(to: str, body: str):
    return await smtp.send(to, body)

# Mode switching based on risk
ledger.set_mode(ExecutionMode.STRICT)  # High-risk scenario
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
from ledger import AuditService, AfterAction

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

## Code Organization by Layer

```
ledger/
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

### Ledger

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

**Framework:**
- [x] Identity (registry, lifecycle)
- [x] Alignment (loyalty, challenges)
- [x] Durable Approvals (async queues)
- [x] Rate Limiting (token bucket)

**Intelligence:**
- [x] Planner (structured planning)
- [x] Critic (quality review)
- [x] Focus (anti-distraction)
- [x] Adaptation (behavioral tuning)
- [x] After Action (learning loop)
- [x] Prune (context cleanup)
- [x] Opportunity (leverage detection)
- [x] Failure (recovery protocol)

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
from ledger import (
    # Kernel
    Ledger, Governor, Constitution, ExecutionMode,
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

# 3. Create Ledger (Enforcement Surface)
ledger = Ledger(
    audit_dsn="postgresql://localhost/ledger",
    governor=gov,
    constitution=constitution
)

# 4. Define Governed Action
@ledger.governed(action="deploy", resource="production")
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

Ledger is **AI governance infrastructure** with three layers:

1. **Kernel** — Runtime enforcement (has teeth)
2. **Framework** — Policy structure (scales)
3. **Intelligence** — Behavioral learning (improves)

This gives you:
- Big company category (AI governance)
- Concrete technical spine (runtime enforcement)
- Competitive moat (36 governance rules already written)
- Fast expansion (1 week per new tool)

**Positioning:**
> Ledger defines, enforces, and proves what AI systems are allowed to do.

**Technical:**
> At its core, Ledger uses runtime enforcement to make governance actionable at the execution boundary.
