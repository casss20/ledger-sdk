# Ledger SDK Product Roadmap

## The Problem (2026)

Teams ship AI agents to production without guardrails:
- ❌ Agent sends 100k emails (prompt bug)
- ❌ Agent deletes production database (wrong permissions)
- ❌ Agent charges customers $50k (loop bug)
- ❌ No audit trail — can't prove what happened
- ❌ No kill switch — can't stop it

## The Solution

**Ledger: Block, Approve, Log, Kill**

- ✅ **Block**: Email, DB writes, payments, external APIs
- ✅ **Require**: Human approval before risky actions
- ✅ **Log**: Every action, tamper-proof, audit-ready
- ✅ **Kill**: Stop any feature instantly, no deploy

Customer reaction: *"Oh fuck, we NEED this. Our agent nearly broke production yesterday."*

---

## 4-Week Implementation Plan

### Week 1: Core Blocking

Wrap the 4 riskiest tool types with `@governed`:

```python
from ledger.sdk import Ledger

gov = Ledger(...)

@gov.governed(action="send_email", resource="outbound_email", flag="email_send")
async def send_email(to: str, subject: str, body: str) -> dict:
    return await smtp.send(to, subject, body)

@gov.governed(action="database_write", resource="production_db", flag="db_write")
async def write_database(query: str, params: dict) -> dict:
    return await db.execute(query, params)

@gov.governed(action="charge_payment", resource="stripe", flag="stripe_charge")
async def stripe_charge(amount: float, customer_id: str) -> dict:
    return await stripe.Charge.create(amount=amount, customer=customer_id)

@gov.governed(action="external_action", resource="github", flag="github_action")
async def github_action(repo: str, action: str, params: dict) -> dict:
    return await github.dispatch(repo, action, params)
```

**Outcome**: Agents can't call these 4 tools without approval.

---

### Week 2: Approval Queue + Simple UI

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ApprovalRequest:
    id: str
    action: str
    resource: str
    risk: str
    args: dict
    created_at: str
    approved: bool | None = None

class ApprovalQueue:
    async def push(self, req: ApprovalRequest): ...
    async def approve(self, req_id: str) -> bool: ...
    async def deny(self, req_id: str) -> bool: ...
    async def get_pending(self) -> list[ApprovalRequest]: ...
    async def wait_for_approval(self, req_id: str, timeout=300) -> bool: ...
```

**Outcome**: Human sees pending approvals, clicks approve/deny, agent execution resumes.

---

### Week 3: Audit Log + Compliance Report

```python
@router.get("/ledger/audit")
async def get_audit_log(action: str | None, approved: bool | None, limit: int = 100): ...

@router.get("/ledger/audit/integrity")
async def verify_audit_integrity():
    ok, entries = await gov.audit.verify_integrity()
    return {"ok": ok, "status": "✅ Chain intact" if ok else "❌ TAMPERING DETECTED"}

@router.get("/ledger/report/compliance")
async def compliance_report(days: int = 7): ...
```

**Outcome**: Teams see exactly what happened, can prove compliance.

---

### Week 4: Kill Switches + Docs

```python
@router.post("/ledger/killswitch/{flag}/kill")
async def kill_switch(flag: str, reason: str):
    gov.killsw.kill(flag, reason=reason)
    return {"status": "killed", "flag": flag}

@router.post("/ledger/killswitch/{flag}/revive")
async def revive_switch(flag: str):
    gov.killsw.revive(flag)
    return {"status": "revived", "flag": flag}
```

**Outcome**: One click, any feature stops. No deploy.

---

## Marketing Angle

**Pitch**: *Ledger: Stop agent accidents before they happen.*

**Integration**: 4 lines of code to wrap a tool  
**Pricing**: $0 open source or $5k consulting install  
**Ongoing**: $99/mo managed dashboard

### Customer Acquisition

- **HackerNews**: "We built an approval queue for AI agents"
- **Reddit**: /r/LocalLLaMA, /r/MachineLearning
- **Discord**: LangChain, CrewAI, OpenAI communities
- **Direct**: YC startups building agents
- **Product Hunt**: "Ledger: AI Governance"

---

## Timeline to Revenue

| Week | Milestone |
|------|-----------|
| 1-2 | Ship 4 wrapped tools + approval queue |
| 3-4 | Audit log + compliance + kill switches |
| 5-6 | Polish, deploy to first customer ($5k) |
| 7-8 | 2nd customer from HN/Discord |
| 9-10 | Release on PyPI, Product Hunt launch |
| Month 4+ | $30k ARR (6 customers × $5k) |

---

## Why This Beats "Broad Governance"

| Competitors (Credo, Arthur, Lakera) | Ledger |
|-------------------------------------|--------|
| ❌ Broad: "AI governance platform" | ✅ Sharp: "Stop agent accidents" |
| ❌ Slow: Days of integration | ✅ Fast: 4 lines of code |
| ❌ Vague: "Monitor for drift" | ✅ Concrete: "Block, approve, log, kill" |
| ❌ Expensive: $2k+/mo | ✅ Cheap: $0 open source |

---

## Implementation Checklist

### Week 1
- [ ] Wrap `send_email()` with `@gov.governed()`
- [ ] Wrap `write_database()` with `@gov.governed()`
- [ ] Wrap `stripe_charge()` with `@gov.governed()`
- [ ] Wrap `github_action()` with `@gov.governed()`
- [ ] Test: verify each tool blocks without approval

### Week 2
- [ ] Build `ApprovalQueue` class
- [ ] Wire `approval_hook()` to queue
- [ ] Build approval API routes
- [ ] Build basic approval HTML UI
- [ ] Test: approve/deny flow

### Week 3
- [ ] Expand audit query endpoints
- [ ] Build compliance report generator
- [ ] Build audit log UI
- [ ] Test: verify integrity endpoint

### Week 4
- [ ] Add kill switch API routes
- [ ] Build kill switch UI
- [ ] Write quick-start docs
- [ ] Test end-to-end: block → approve → execute → audit → kill

### Deploy
- [ ] Run against production test agent
- [ ] Verify no false negatives
- [ ] Verify approval queue under load
- [ ] Get first customer to test

---

## Current Status

| Component | Status |
|-----------|--------|
| Core SDK (`@governed`, kill switches, audit) | ✅ Complete |
| Constitution (24 markdown files) | ✅ Complete |
| FastAPI integration example | ✅ Complete |
| Approval queue | 🔄 Week 2 |
| Dashboard UI | 🔄 Week 3-4 |
| PyPI release | 🔄 Week 9-10 |

---

*Built for agent-world. Ready for production.*
