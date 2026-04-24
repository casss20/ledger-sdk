# CITADEL: AI Governance Architecture

## Positioning Statement

**CITADEL is AI governance infrastructure for production AI systems.**

Its kernel is runtime enforcement, so governance is not just observed â€” it is enforced.

---

## The Three-Layer Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    GOVERNANCE INTELLIGENCE                   â”‚
â”‚     (Alignment, Planning, Adaptation, Focus, Learning)      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                    GOVERNANCE FRAMEWORK                      â”‚
â”‚     (Policy, Identity, Approvals, Lifecycle, Versioning)    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                    GOVERNANCE KERNEL                         â”‚
â”‚     (Enforcement, Deterministic Policy, Audit, Kill)        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
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

- Policy hierarchy (Constitution â†’ World â†’ User Request)
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

CITADEL exposes three surfaces to users:

### Surface 1: Governance Controls
**What policy exists?**

```python
from CITADEL import Constitution, Governor, Alignment

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
from CITADEL import CITADEL, ExecutionMode

CITADEL = CITADEL(audit_dsn="postgresql://...")

# Runtime enforcement at action boundary
@citadel.governed(action="send_email", resource="outbound")
async def send_email(to: str, body: str):
    return await smtp.send(to, body)

# Mode switching based on risk
CITADEL.set_mode(ExecutionMode.STRICT)  # High-risk scenario
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
from CITADEL import AuditService, AfterAction

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

- âŒ "Monitoring" â€” too passive, no enforcement
- âŒ "Guardrails" â€” too vague, not systematic
- âŒ "Runtime blocking only" â€” too narrow, misses framework
- âŒ "Policy theater" â€” documentation without enforcement

---

## Technical Spine: Runtime as Kernel

### Why Runtime is Non-Negotiable

```
Without Runtime:
â”œâ”€ Policy exists in documents
â”œâ”€ Violations are logged
â”œâ”€ Humans review after the fact
â””â”€ Governance = observation

With Runtime:
â”œâ”€ Policy is code
â”œâ”€ Violations are blocked
â”œâ”€ Approvals happen before execution
â””â”€ Governance = enforcement
```

### Runtime Enforcement Points

```
Agent â†’ Action Request
        â†“
   [GOVERNOR] â† Escalation check
        â†“
   [CONSTITUTION] â† Behavioral rules
        â†“
   [ALIGNMENT] â† Long-term goal check
        â†“
   [RISK] â† Classification (SOFT/HARD)
        â†“
   [CAPABILITY] â† Token issuance
        â†“
   [EXECUTOR] â† Execution with monitoring
        â†“
   [AUDIT] â† Immutable log
```

---

## Code Organization by Layer

```
CITADEL/
â”œâ”€â”€ core/                    # GOVERNANCE KERNEL
â”‚   â”œâ”€â”€ governor.py          # Strategic oversight
â”‚   â”œâ”€â”€ executor.py          # Execution enforcement
â”‚   â”œâ”€â”€ runtime.py           # Activation cycle
â”‚   â””â”€â”€ constitution.py      # Behavioral constraints
â”‚
â”œâ”€â”€ governance/              # KERNEL + FRAMEWORK + INTELLIGENCE
â”‚   â”œâ”€â”€ capability.py        # Kernel: tokens
â”‚   â”œâ”€â”€ risk.py              # Kernel: classification
â”‚   â”œâ”€â”€ audit.py             # Kernel + Evidence: logging
â”‚   â”œâ”€â”€ killswitch.py        # Kernel: emergency stop
â”‚   â”œâ”€â”€ rate_limit.py        # Framework: throttling
â”‚   â”œâ”€â”€ durable.py           # Framework: approvals
â”‚   â”œâ”€â”€ alignment.py         # Framework: loyalty
â”‚   â”œâ”€â”€ critic.py            # Intelligence: quality
â”‚   â”œâ”€â”€ prune.py             # Intelligence: cleanup
â”‚   â””â”€â”€ after_action.py      # Intelligence: learning
â”‚
â”œâ”€â”€ ops/                     # INTELLIGENCE
â”‚   â”œâ”€â”€ planner.py           # Structured planning
â”‚   â”œâ”€â”€ failure.py           # Recovery protocol
â”‚   â”œâ”€â”€ adaptation.py        # Behavioral adjustment
â”‚   â””â”€â”€ opportunity.py       # Leverage detection
â”‚
â””â”€â”€ system/                  # INTELLIGENCE
    â””â”€â”€ focus.py             # Anti-distraction
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

### CITADEL

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

### âœ… Complete (Production Ready)

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

### â³ Pending (Defined in MD files)

- [ ] HEARTBEAT (system health polling)
- [ ] SELF-MOD (policy evolution)
- [ ] START (boot orchestration)
- [ ] WORLD (goal hierarchy)
- [ ] USER (relationship model)
- [ ] MEMORY (context management)

---

## Usage: Full Stack Example

```python
from CITADEL import (
    # Kernel
    CITADEL, Governor, Constitution, ExecutionMode,
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

# 3. Create CITADEL (Enforcement Surface)
CITADEL = CITADEL(
    audit_dsn="postgresql://localhost/CITADEL",
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

CITADEL is **AI governance infrastructure** with three layers:

1. **Kernel** â€” Runtime enforcement (has teeth)
2. **Framework** â€” Policy structure (scales)
3. **Intelligence** â€” Behavioral learning (improves)

This gives you:
- Big company category (AI governance)
- Concrete technical spine (runtime enforcement)
- Competitive moat (36 governance rules already written)
- Fast expansion (1 week per new tool)

**Positioning:**
> CITADEL defines, enforces, and proves what AI systems are allowed to do.

**Technical:**
> At its core, CITADEL uses runtime enforcement to make governance actionable at the execution boundary.
