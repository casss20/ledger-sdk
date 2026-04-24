# FORGE Expansion Roadmap

## Phase 1: The Sharp Wedge (Month 1-3) â€” 4 Core Controls

Start narrow. Nail it.

```
Block email
Block database writes
Block payments (Stripe)
Block code commits (GitHub)

= "Runtime approval for the 4 most dangerous agent actions"
```

**Why 4?** These are the ones that:
- Have immediate customer pain (100k emails, data deletion, wrong charges, code injection)
- Are easy to measure ROI on ("we prevented $50k loss")
- Give customers the "oh fuck, we need this" moment instantly

**Focus:** Get to $10k MRR with these 4. Land 3-5 customers. Perfect the approval flow.

---

## Phase 2: Add More Tools (Month 4-6) â€” Leverage CITADEL's Stack

Once 4 core controls are solid, CITADEL gives you **everything else for free**.

Your CITADEL/core/*.md files already define governance for ALL of these:

### Tier 1: Production Risk (Immediate value, 2 weeks each)

```
âœ… Done: Email blocking
âœ… Done: Database writes
âœ… Done: Stripe charges
âœ… Done: GitHub commits

Now add (Month 4-6):
ðŸ”œ Slack messaging (from COMMUNICATION.md rules)
ðŸ”œ API rate limiting (from EXECUTOR.md + AUTONOMY.md)
ðŸ”œ Data export/download (from FOCUS.md scope rules)
ðŸ”œ CRM record updates (from TOOLS.md policy)
ðŸ”œ External API calls (from CONSTITUTION.md external guardrail)
```

**How it works:** Each new tool = new policy pack from CITADEL/core/. Load the right markdown, reuse the approval engine.

**Example: Slack messaging**

```python
@gov.governed(action="send_message", resource="slack")
async def send_slack_message(channel: str, body: str) -> dict:
    # Read from CONSTITUTION.md:
    # "External actions require approval"
    #
    # Read from COMMUNICATION.md (new):
    # "Messages > 5k chars â†’ content review"
    # "Messages to #general or #leadership â†’ approval required"
    #
    # Read from TOOLS.md:
    # "Slack posting limited to 100 msgs/hour"

    # Same enforcement engine
    # Same approval queue
    # Same audit trail
    return await slack.post(channel, body)
```

---

### Tier 2: Compliance + Identity (Month 7-9)

Your CITADEL already has MEMORY.md + USER.md + IDENTITY.md:

```
ðŸ”œ Customer data access (from MEMORY.md scope rules)
ðŸ”œ PII redaction checks (from USER.md + GDPR rules)
ðŸ”œ Agent identity switching (from IDENTITY.md modes)
ðŸ”œ Multi-agent coordination (from AGENTS.md)
ðŸ”œ Cross-agent approvals (from GOVERNOR.md escalation)
```

**Example: Customer data access**

```python
@gov.governed(action="query_customer_data", resource="customer_db")
async def get_customer_data(customer_id: str, fields: list[str]) -> dict:
    # Read from MEMORY.md:
    # "High-value customers (revenue > $10k) â†’ manual approval for data access"
    #
    # Read from USER.md:
    # "Personal data (SSN, CC, DOB) â†’ always approval required"
    #
    # Risk scoring based on data sensitivity

    return await db.query(customer_id, fields)
```

---

### Tier 3: Operational Efficiency (Month 10-12)

Your CITADEL has RUNTIME.md + FAILURE.md + AUTONOMY.md:

```
ðŸ”œ LLM cost control (from AUTONOMY.md budget rules)
ðŸ”œ API quota enforcement (from RUNTIME.md selective loading)
ðŸ”œ Cascading loop detection (from FAILURE.md cascade rules)
ðŸ”œ Agent timeout override (from EXECUTOR.md modes)
ðŸ”œ Resource limits (CPU/RAM)(from PRUNE.md cleanup)
```

**Example: LLM cost control**

```python
@gov.governed(action="llm_call", resource="gpt4_calls", flag="gpt4_expensive")
async def call_gpt4(prompt: str, tokens: int) -> dict:
    # Read from AUTONOMY.md:
    # "Agent nova budget: $100/day for LLM calls"
    # "Current spend: $87. Tokens requested: 2000 (~$5)"
    # "Remaining: $13. This call is OK."
    #
    # If over budget:
    # "Budget exceeded. Use GPT-3.5 instead?"

    if tokens_cost(tokens) > remaining_budget:
        return {"blocked": True, "reason": "budget exceeded", "suggestion": "use gpt35"}

    return await openai.complete(prompt)
```

---

### Tier 4: Shadow Agent Discovery + Security (Month 13+)

Your CITADEL has AGENTS.md + SECURITY.md patterns:

```
ðŸ”œ Agent inventory (all tool calls logged â†’ who's running?)
ðŸ”œ Unauthorized agent spawn (from FOCUS.md bouncer protocol)
ðŸ”œ Prompt injection defense (from CONSTITUTION.md guardrails)
ðŸ”œ Tool call anomalies (from GOVERNOR.md pattern detection)
ðŸ”œ Agent jailbreak attempts (from FAILURE.md failure handling)
```

---

## The Architecture: Why This Scales

### Core Loop (Same for all 50+ use cases)

```
Agent calls tool
 â”‚
 â–¼
FORGE GATEWAY
 â”‚
 â”œâ”€ Identify tool type
 â”œâ”€ Load policy from CITADEL/core/*.md
 â”œâ”€ Score risk (GOVERNOR.md)
 â”œâ”€ Apply enforcement (allow/block/approve)
 â”œâ”€ Log to audit trail
 â”‚
 â””â”€ Execute or route

Same engine.
Same approval queue.
Same audit trail.
Different policy packs.
```

### Adding a New Tool Takes 1 Week

**Example: Add "Slack messaging" control in Week 1 of Month 4**

```
Step 1: Identify the policy
 Read CITADEL/core/COMMUNICATION.md (already written for Slack)
 Read CITADEL/core/CONSTITUTION.md (external action rules)

Step 2: Create the policy pack
 slug: "slack_messaging"
 rules: [
   "Messages to #general â†’ approval required",
   "Messages > 5k chars â†’ content review",
   "Rate limit: 100 msgs/hour per agent"
 ]

Step 3: Wire the tool
 @gov.governed(action="send_slack", resource="slack", policy="slack_messaging")
 async def send_slack_message(channel, body):
     return await slack.post(channel, body)

Step 4: Test
 Agent calls Slack â†’ blocked â†’ routed to approval â†’ log written

Done. Time: 1 day.
```

### Why Competitors Can't Match This

They'd have to:
1. Build governance framework (6 months)
2. Wire first 4 tools (2 months)
3. Add next 10 tools (2 months each = 20 months)

**Total: 28 months** to get where you are in month 12.

You: 1 week per tool after the core is built.
Competitor: 2+ months per tool.

**Your moat:** You have the governance rules written. They don't.

---

## CITADEL's Hidden Superpowers (You don't have to build these, you inherit them)

### From GOVERNOR.md
```
Escalation levels 0-3
â”œâ”€ Level 0: Auto-allow (fast, obvious tasks)
â”œâ”€ Level 1: Log + alert (medium risk)
â”œâ”€ Level 2: Require approval (high risk)
â””â”€ Level 3: Lock execution + human intervention (critical)

Applies to ALL tools.
```

### From RUNTIME.md
```
Path selection
â”œâ”€ Fast path (email to trusted contact â†’ no approval)
â”œâ”€ Standard (email to unknown â†’ approval)
â”œâ”€ Structured (bulk email > 100 â†’ approval + content review)
â””â”€ High-risk (email + suspicious content â†’ approval + security review)

Same logic works for all tools.
```

### From AUDIT.md
```
Every decision logged:
â”œâ”€ Who (agent name + identity mode)
â”œâ”€ What (tool, action, args)
â”œâ”€ When (timestamp)
â”œâ”€ Why (policy, risk score, decision)
â”œâ”€ Who approved (human name + time)
â””â”€ Hash chain (tamper-proof)

Same format for all tools.
All searchable. All compliant.
```

### From SELF-MOD.md
```
Policies can be updated without redeployment:
â”œâ”€ User writes new policy in UI
â”œâ”€ System stages it
â”œâ”€ User approves
â”œâ”€ Policy live in 30 seconds
â””â”€ No code deploy, no restart

Works for all tools.
```

---

## Expansion Timeline: From 4 to 50+ Controls

```
Month 1-3: Core 4 (email, DB, Stripe, GitHub)
â””â”€ $10k MRR

Month 4-6: Add 8 more tools
â”œâ”€ Slack, API calls, CRM, data export, rate limiting, ...
â””â”€ $30k MRR

Month 7-9: Add compliance tier (customer data, PII, identity modes)
â”œâ”€ +6 controls
â”œâ”€ Target: Regulated industries (finance, healthcare)
â””â”€ $75k MRR

Month 10-12: Add operational tier (costs, quotas, loops, timeouts)
â”œâ”€ +6 controls
â”œâ”€ Target: Large enterprises running 50+ agents
â””â”€ $150k MRR

Year 2: Add shadow discovery + security tier
â”œâ”€ +12 controls
â”œâ”€ Agent inventory, anomaly detection, jailbreak defense
â”œâ”€ Target: Security + compliance teams
â””â”€ $500k+ MRR
```

---

## The Pricing Impact: More Tools = More Revenue

```
Month 3:
 5 customers Ã— 5 agents Ã— $99 = $2,475/month = $30k/year

Month 6:
 10 customers Ã— 15 agents Ã— $99 = $14,850/month = $178k/year

Month 9:
 20 customers Ã— 25 agents Ã— $149 (Pro+ tier) = $74,500/month = $900k/year
 (Customers upgrade to Pro+ for compliance controls)

Month 12:
 30 customers Ã— 40 agents Ã— $199 (Enterprise-lite) = $239,600/month = $2.8M/year
 (Customers upgrade for shadow discovery + security)
```

**Why pricing goes up:**
- More controls = more value
- Compliance controls = enterprise customers
- Security controls = security teams (higher budgets)

---

## What NOT to Do

### âŒ Build all 50 at once
You'll be done in year 3. Competitors will have launched by then.

### âŒ Add random tools
Add based on customer demand, not your ideas. Let the market tell you what hurts.

### âŒ Forget the CITADEL
Every tool should map back to a CITADEL/*.md file. If it doesn't, you're building off-brand.

### âŒ Drop the wedge
Never stop iterating on the core 4. They're your revenue engine. Optimizing approval workflows, reducing false positives, improving UXâ€”this never stops.

---

## What TO Do

### âœ… Perfect the wedge first
Month 1-3: Make the core 4 *bulletproof*.
- 0% false positives (customers trust it)
- <100ms latency (no slowdown)
- 99.9% uptime (never breaks)

### âœ… Let customers drive expansion
"Which tool would you want Forge to control next?"
Listen. Don't guess.

### âœ… Reuse the CITADEL
Every new tool = read the markdown you already wrote.
Markdown â†’ Policy pack â†’ Wire tool â†’ Done in 1 week.

### âœ… Price the value
Email control = $99/agent. Data control = $199/agent. Security control = $399/agent.
More tools = higher tier = more revenue per customer.

### âœ… Market the expansion
"We now control 12 types of agent actions."
"We now support 25+ integrations."
"We're the most comprehensive AI agent governance platform."

---

## The CITADEL Advantage: Why You Win Long-Term

### Competitors (Credo, Arthur, Lakera)
```
Month 1: Build framework
Month 2: Add email control
Month 3: Add DB control
Month 4-12: Add payment, GitHub, Slack, CRM, ...
Year 2: Still building individual tools

Cost: $2M+ engineering
Time: 18+ months to full platform
```

### You
```
Month 1: Build framework + 4 core tools
Month 2-12: Add 20+ tools (1 week each)
Year 2: 50+ controls, full platform

Cost: $500k engineering
Time: 6 months to full platform

Why? You already wrote the governance rules in CITADEL/core/*.md.
You're not inventing policies. You're implementing them.
```

---

## Specific Tools to Add (In Priority Order)

### Q1 (Month 4-6): Critical
- [ ] Slack messaging approval
- [ ] API rate limiting
- [ ] Data export/download approval
- [ ] CRM record updates (Salesforce, HubSpot)
- [ ] Customer data queries
- [ ] LLM cost tracking

### Q2 (Month 7-9): Compliance
- [ ] PII redaction + masking
- [ ] GDPR-specific rules (EU customers)
- [ ] Agent identity switching (mode toggles)
- [ ] Multi-agent workflows (one agent calls another)
- [ ] SOC2 compliance packs
- [ ] Audit report generation

### Q3 (Month 10-12): Operations
- [ ] LLM budget enforcement
- [ ] API quota management
- [ ] Cascading loop detection
- [ ] Agent spawn controls
- [ ] Timeout enforcement
- [ ] Resource limits (CPU/RAM)

### Q4 (Year 2): Security
- [ ] Agent inventory + discovery
- [ ] Unauthorized agent detection
- [ ] Prompt injection defense
- [ ] Tool call anomaly detection
- [ ] Jailbreak attempt logging
- [ ] Supply chain attack prevention

---

## Revenue Per Tool

```
Email control: $0 (included in base)
Database control: $0 (included in base)
Payment control: $0 (included in base)
Code commit control: $0 (included in base)

Add Slack control: +$20/agent/month â†’ Pro+ tier
Add CRM control: +$20/agent/month â†’ Pro+ tier
Add API rate limit: +$20/agent/month â†’ Pro+ tier

= Pro tier ($99) â†’ Pro+ tier ($159)

Add GDPR compliance: +$50/agent/month â†’ Enterprise tier
Add audit reports: +$50/agent/month â†’ Enterprise tier
Add agent inventory: +$50/agent/month â†’ Enterprise tier

= Pro+ tier ($159) â†’ Enterprise tier ($299)
```

**5 tools added = 3x pricing = 3x revenue per customer.**

---

## Bottom Line

**You're not building a list of tools. You're building a platform.**

The wedge (4 core tools) gets you in the door.

The CITADEL (your 36 markdown files + 8-layer architecture) lets you scale to 50+ controls *without rewriting the governance engine*.

Competitors see 50 separate problems.
You see 1 governance framework, 50 policy packs.

**Phase 1:** Nail 4 controls, $10k MRR
**Phase 2:** Scale to 20+ controls, $100k MRR
**Phase 3:** Own the space (50+ controls), $1M+ MRR

Same core engine. Different tools. Infinite scale.

That's the moat.
