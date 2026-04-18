# ARCHITECTURE.md — How Ledger and the Governance Layer Works

**Document Purpose:** Deep technical explanation of Ledger's internal architecture and data flow.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR AI AGENT CODE                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  @gov.governed(action="send_email", resource="outbound")│   │
│  │  async def send_email(to, body):                        │   │
│  │      return await smtp.send(to, body)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LEDGER SDK (@governed)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ 1. Capture  │ │ 2. Classify │ │ 3. Check    │ │ 4. Decide │ │
│  │    Action   │ │    Risk     │ │    Policy   │ │    Fate   │ │
│  │             │ │             │ │             │ │           │ │
│  │  action_id  │ │  LOW/MED/   │ │  Kill sw?   │ │  ALLOW /  │ │
│  │  agent      │ │    HIGH     │ │  Rate lim?  │ │  BLOCK /  │ │
│  │  resource   │ │             │ │  Approval?  │ │  ASK HUMAN│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
┌─────────────────────┐     ┌─────────────────────┐
│   GOVERNOR (State)  │     │   AUDIT (Immutable) │
│                     │     │                     │
│  Tracks everything  │     │  Hash-chained logs  │
│  - PENDING          │     │  - Who did what     │
│  - EXECUTING        │     │  - When             │
│  - SUCCESS/FAILED   │     │  - Risk level       │
│  - SKIPPED          │     │  - Approved?        │
│  - DEFERRED         │     │                     │
└─────────────────────┘     └─────────────────────┘
```

---

## The Flow (Step by Step)

### 1. Capture — Action Starts

When you decorate a function with `@governed`:

```python
from ledger import Ledger

gov = Ledger(audit_dsn="postgresql://...")

@gov.governed(action="send_email", resource="outbound_email", flag="email_send")
async def send_email(to: str, body: str):
    return await smtp.send(to, body)
```

When `send_email()` is called, Ledger immediately:
- Generates `action_id` (UUID)
- Creates record in **GOVERNOR** (state = PENDING)
- Logs to **AUDIT** (attempt started)

### 2. Classify — What's the Risk?

Built-in risk matrix:

```python
# From ledger/governance/risk.py
ACTION_RISKS = {
    "read":          (Risk.LOW,    Approval.NONE),   # Safe
    "search":        (Risk.LOW,    Approval.NONE),   # Safe
    "write_file":    (Risk.MEDIUM, Approval.SOFT),   # Maybe ask
    "send_email":    (Risk.HIGH,   Approval.HARD),   # Always ask
    "delete":        (Risk.HIGH,   Approval.HARD),   # Always ask
    "deploy":        (Risk.HIGH,   Approval.HARD),   # Always ask
}
```

**Risk levels:**
- **LOW** → Auto-approve
- **MEDIUM** → Maybe ask (configurable)
- **HIGH** → Human approval required

### 3. Check — Policy Enforcement

```
┌────────────────────────────────────┐
│  KILL SWITCH CHECK                 │
│  Is flag "email_send" disabled?    │
│  → YES: Block immediately (DENIED) │
│  → NO: Continue                    │
└──────────────┬─────────────────────┘
               ▼
┌────────────────────────────────────┐
│  RATE LIMIT CHECK                  │
│  Too many emails this hour?        │
│  → YES: Block (RATE_LIMITED)       │
│  → NO: Continue                    │
└──────────────┬─────────────────────┘
               ▼
┌────────────────────────────────────┐
│  APPROVAL CHECK                    │
│  HIGH risk + no prior approval?    │
│  → YES: Queue for human review     │
│  → NO: Execute now                 │
└────────────────────────────────────┘
```

### 4. Decide — Three Outcomes

| Outcome | What Happens | Governor State |
|---------|--------------|----------------|
| **ALLOW** | Execute function, log success | SUCCESS |
| **BLOCK** | Raise `Denied`, log rejection | DENIED |
| **ASK** | Queue for human, wait for response | PENDING → (APPROVED/DENIED) |

---

## The Components

### 1. Ledger SDK (`sdk.py`)

**Role:** The decorator and executor

**Responsibilities:**
- Wraps your functions with `@governed`
- Orchestrates the governance flow
- Issues capability tokens
- Handles errors and retries
- Reports state transitions to Governor

**Key Class:** `Ledger`
```python
class Ledger:
    def __init__(self, audit_dsn: str, agent: str = "default"):
        self.caps = CapabilityIssuer()      # Token management
        self.audit = AuditService(dsn)       # Audit logging
        self.killsw = KillSwitch()           # Emergency stops
        self.governor = get_governor()       # State tracking
    
    def governed(self, action: str, resource: str, flag: str = None):
        # Returns decorator that wraps functions
```

### 2. Governor (`governor.py`)

**Role:** Single source of truth for action state

**Tracks:**
```
PENDING → EXECUTING → SUCCESS
   ↓
DEFERRED (human approval)
   ↓
APPROVED → EXECUTING → SUCCESS
   ↓
DENIED
```

**Key Methods:**
```python
gov = get_governor()

gov.create(action_id, action, resource, agent, risk)
gov.transition(action_id, ActionState.EXECUTING)
gov.transition(action_id, ActionState.SUCCESS)

gov.list_pending()     # What's waiting?
gov.list_failed()      # What broke?
gov.list_skipped()     # What was skipped?
gov.get_summary()      # Dashboard data
```

### 3. Audit (`governance/audit.py`)

**Role:** Tamper-proof logging

**Features:**
- Hash-chained logs (can't modify history)
- Postgres storage
- Query interface: "Show me all HIGH risk actions from yesterday"

**Schema:**
```python
{
    "actor": "my-agent",
    "action": "send_email",
    "resource": "outbound_email",
    "risk": "high",
    "approved": True,
    "timestamp": "2026-04-19T06:00:00Z",
    "hash": "sha256:abc123...",  # Chain of custody
    "payload": {...}  # Action details
}
```

### 4. Kill Switch (`governance/killswitch.py`)

**Role:** Emergency brake

```python
# Instantly disable features
gov.killsw.kill("email_send", reason="spam outbreak")
gov.killsw.kill("payments", reason="fraud detected")
gov.killsw.kill("deployments", reason="incident in progress")

# Check before executing
if not gov.killsw.is_enabled("email_send"):
    raise Denied("Feature disabled by kill switch")
```

**No deploy required.** Kill switches work immediately.

### 5. Capability Issuer (`governance/capability.py`)

**Role:** Token-based permission system

```python
# Issue a capability token
cap = gov.caps.issue(
    action="send_email",
    resource="outbound_email",
    ttl_seconds=120,
    max_uses=1,
    issued_to="my-agent"
)

# Token format: cryptographically signed
# cap.token = "ledger:eyJhbGciOiJIUzI1NiIs..."

# Consume the token (one-time use)
gov.caps.consume(cap.token)
```

**Purpose:** Even if code is compromised, tokens expire and are limited-use.

### 6. Error Handling (`error_handling.py`)

**Role:** Resilience patterns

```python
from ledger import try_governed, Retry, Catch, Default

@try_governed(Retry(times=3, backoff=2.0))
@gov.governed(action="stripe_charge")
async def charge_customer(amount: float):
    return await stripe.charges.create(amount=amount)

@try_governed(Catch(fallback_fn=notify_admin))
@gov.governed(action="send_critical_alert")
async def send_alert(message: str):
    return await smtp.send(to="admin@company.com", body=message)
```

**Strategies:**
- `Retry(times, backoff)` — Exponential backoff retries
- `Catch(fallback_fn)` — Route to handler on failure
- `Default(value)` — Return default on failure
- `DeadLetter()` — Queue for manual review

### 7. Analytics (`analytics.py`)

**Role:** Detect anomalies

```python
from ledger import get_analytics, TimeWindow

analytics = get_analytics()

# Detect "50 emails in 1 minute"
metrics = await analytics.analyze_window(TimeWindow.last_minute())

if metrics["send_email"].is_anomalous:
    # ALERT: Rate spike detected!
    await send_slack_alert("Agent spamming emails!")
```

**Detects:**
- Rate spikes (5x baseline)
- Failure spikes (>30% failure rate)
- High-risk bursts (>10 HIGH risk actions)
- Pattern breaks (outside normal hours)

### 8. Durable Execution (`governance/durable.py`)

**Role:** Survive restarts

```python
# Human approval that takes 3 days
promise = DurablePromise(
    promise_id="req_abc123",
    action="deploy_production",
    risk="HIGH"
)

# Persist to Redis (survives server restart)
await promise.persist()

# Wait for approval (with exponential backoff)
approved = await promise.wait(timeout_sec=259200)  # 3 days
```

**Use case:** Long-running approvals, human-in-the-loop workflows.

---

## Data Flow Example

```
User calls: send_email("ceo@company.com", "Urgent")

1. LEDGER captures:
   action_id = "abc-123"
   action = "send_email"
   risk = HIGH
   agent = "my-bot"
   
   GOVERNOR state: PENDING

2. Checks:
   Kill switch? → OK
   Rate limit? → OK
   Approval? → HIGH risk, needs human

3. Goes to approval queue
   (Human gets Slack/Email notification)
   GOVERNOR state: DEFERRED

4. Human approves via dashboard
   (3 minutes later)
   GOVERNOR state: EXECUTING

5. LEDGER executes:
   await smtp.send(...)
   → SUCCESS
   
   GOVERNOR state: SUCCESS
   completed_at = 2026-04-19T06:05:00Z

6. AUDIT logs:
   actor: my-bot
   action: send_email
   risk: high
   approved: true
   approved_by: human@company.com
   hash: sha256:abc123...
   
7. ANALYTICS updates:
   send_email count: +1
   (No anomaly this time)
```

---

## The Governance Layer Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE LAYER                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   RISK   │  │   RATE   │  │   KILL   │  │  AUDIT   │    │
│  │  MATRIX  │  │  LIMIT   │  │  SWITCH  │  │   LOG    │    │
│  │          │  │          │  │          │  │          │    │
│  │ What can │  │ How many │  │ Emergency│  │ What     │    │
│  │  go wrong│  │  per min?│  │   stop?  │  │ happened?│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ APPROVAL │  │   ERROR  │  │  ANALYTICS│  │  GOVERNOR│   │
│  │  QUEUE   │  │ HANDLING │  │          │  │  (STATE) │    │
│  │          │  │          │  │          │  │          │    │
│  │ Human in │  │ Retry/   │  │ Detect   │  │ Track    │    │
│  │   loop   │  │ Fallback │  │ anomalies│  │  all     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
        ▲                                  ▲
        │                                  │
   Your Agent                        Dashboard/API
```

---

## Key Design Decisions

### 1. Separation of Concerns

**Ledger (sdk.py):** Owns execution
- Runs the governance checks
- Executes your code
- Reports to Governor

**Governor (governor.py):** Owns visibility
- Tracks state
- Answers queries
- Never controls execution

**Why:** Clean architecture, testable, no circular dependencies

### 2. Immutable Audit Trail

Every action is logged with a hash chain:
```
Record N: { data, prev_hash: hash(N-1) }
Record N+1: { data, prev_hash: hash(N) }
```

**Why:** Tamper-evident. If you modify history, hashes don't match.

### 3. Async-First Design

All governance operations are async:
```python
@gov.governed(action="...")
async def my_function():
    ...
```

**Why:** Non-blocking I/O for audit logs, approval queues, rate limit checks.

### 4. Optional Dependencies

```bash
pip install ledger-sdk              # Core only
pip install ledger-sdk[durable]     # + Redis
pip install ledger-sdk[fastapi]     # + FastAPI
pip install ledger-sdk[all]         # Everything
```

**Why:** Keep core lightweight, add features as needed.

---

## Without Ledger vs With Ledger

### Without Ledger
```python
async def send_email(to, body):
    # No protection. Accidents happen.
    return await smtp.send(to, body)

# What can go wrong:
# - Sends 10,000 emails at 3 AM
# - No record of who/when
# - Can't stop it during incident
# - No approval for sensitive sends
```

### With Ledger
```python
@gov.governed(action="send_email", flag="email_send")
async def send_email(to, body):
    return await smtp.send(to, body)

# What happens now:
# ✅ Risk checked before execution
# ✅ Kill switch can disable instantly
# ✅ Rate limited (no spam)
# ✅ Human approves if HIGH risk
# ✅ Every send logged with hash chain
# ✅ Anomalies detected automatically
# ✅ Retries on failure
```

**Same code. 4 lines of protection.**

---

## Summary

**Ledger is the immune system for AI agents:**

1. **Capture** — Wrap functions with `@governed`
2. **Classify** — Auto-detect risk level
3. **Check** — Policy enforcement (kill switches, rate limits, approvals)
4. **Decide** — Allow, block, or ask human
5. **Track** — Governor + Audit trail for everything
6. **Analyze** — Detect anomalies, monitor health

**Result:** AI agents that can't accidentally break things.

---

**Document Owner:** Anthony Cass  
**Created:** 2026-04-19  
**Status:** Architecture Reference  
**Related:** VISION.md, ROADMAP.md, ARCHITECTURE_DECISION.md