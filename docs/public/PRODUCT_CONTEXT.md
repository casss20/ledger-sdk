# Citadel SDK â€” Shared Product Context for Documentation Writers

## Product Overview

Citadel SDK is a governance layer for AI agents. It embeds compliance, audit, and control directly into agent runtime â€” making governance non-optional and non-bypassable. Think "Stripe for AI governance" â€” infrastructure that becomes embedded, then indispensable.

## Technical Design Pillars

1. **Unified Commercial Identity**: Bridging Stripe billing, OAuth identity, and GT tokenization into a single, governed execution context.
2. **The Dual-Write Governance Pipeline**: Ensuring that every proposed action and its final decision are persisted in a tamper-proof, append-only audit chain.
3. **The Hardened Runtime (RLS + OTel + Kill Switch)**: Combining PostgreSQL RLS, OpenTelemetry for observability, and Global Kill Switches for production safety.

## Architecture Components

### 1. Governance Kernel (Hardened Runtime)
- Intercepts all agent tool calls at runtime
- Evaluates policies against every action before execution
- Cannot be bypassed by application code (enforced at infrastructure layer)
- Equivalent to PostgreSQL RLS query rewriter â€” policies applied before execution

### 2. RLS Auth (Row-Level Security for Agents)
- Per-agent identity with cryptographically signed tokens
- Agent-to-agent authentication via `gt_` governance tokens
- Tenant isolation for multi-agent deployments
- Role-based access control with 5 role types: Executive, Admin, Operator, Analyst, Auditor

### 3. Hash-Chained Audit Trail
- Every agent action recorded with SHA-256 hash
- Chain hash links each record to previous (tamper-evident)
- Dual-write: immutable archive (S3 Object Lock COMPLIANCE mode) + searchable index
- W3C trace context correlation across distributed agents
- 6-month minimum retention (EU AI Act Article 12 compliant)

### 4. Commercial Billing & Entitlements
- **Stripe-Backed Plans**: Dynamic subscription management (Free, Pro, Enterprise).
- **Quota Enforcement**: Automated 429 (Too Many Requests) responses when tenant limits are reached.
- **Payment Grace Period**: Automatic 402 (Payment Required) status for `past_due` accounts with a 7-day access buffer.
- **Atomic Usage Tracking**: High-concurrency Postgres counters for precise usage metering.

### 5. Kill Switch (Human Oversight)
- Emergency halt mechanism for any agent or agent group
- EU AI Act Article 14(4)(e) "stop button or similar procedure" compliant
- Circuit breaker pattern for automatic degradation
- Human-in-the-loop approval queue for high-risk actions

## Key Concepts

### Governance Tokens (`gt_`)
- Opaque token format (e.g., `gt_1Aa2Bb3Cc4Dd`)
- References governance decisions stored in CITADEL's vault
- Non-portable â€” only resolvable by CITADEL
- Creates data gravity: accumulated governance history increases switching cost
- Analogous to Stripe's `pm_` PaymentMethod tokens

### Policy Syntax (YAML)
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: refund-approval-over-1000
  namespace: payments
spec:
  trigger:
    action: refund.create
    condition: amount > 1000
  enforcement:
    type: require_approval
    approvers: [finance-manager]
    timeout: 24h
  audit:
    level: comprehensive
    retention: 7years
```

### Enforcement Types
- `allow` â€” Pass through (logged only)
- `deny` â€” Block action
- `require_approval` â€” Hold for human approval
- `rate_limit` â€” Throttle to N per window
- `require_auth` â€” Demand additional agent authentication
- `alert_only` â€” Log and notify, don't block

### Trust Scoring
- Each agent has a real-time trust score (0-1000)
- Factors: action history, anomaly detection, policy compliance rate, human override frequency
- Score below threshold triggers elevated monitoring or automatic kill switch
- Analogous to credit score for agents

## SDK APIs

### Python SDK
```python
import citadel_sdk

# Initialize with API key
CITADEL = citadel_sdk.Client(api_key="ldk_...")

# Wrap an agent action
governed = citadel.govern(
    agent_id="agent-123",
    action="email.send",
    params={"to": "user@example.com", "subject": "..."}
)

# Execute with automatic policy enforcement
result = governed.execute()
```

### TypeScript SDK
```typescript
import { CITADELClient } from '@citadel/sdk';

const CITADEL = new CITADELClient({ apiKey: 'ldk_...' });

const governed = citadel.govern({
  agentId: 'agent-123',
  action: 'email.send',
  params: { to: 'user@example.com', subject: '...' }
});

const result = await governed.execute();
```

### Go SDK
```go
import "github.com/CITADEL/sdk-go"

CITADEL := sdk.NewClient(sdk.Config{APIKey: "ldk_..."})

governed := citadel.govern(sdk.GovernanceRequest{
    AgentID: "agent-123",
    Action:  "email.send",
    Params:  map[string]interface{}{"to": "user@example.com"},
})

result, err := governed.Execute()
```

## Dashboard (Stream 3b)
- **Governance Posture Score** â€” Unified health metric (0-100%)
- **Activity Stream** â€” Prioritized violation queue (Datadog Security Inbox pattern)
- **Coverage Heatmap** â€” Policy enforcement density across AI lifecycle
- **Kill Switch Panel** â€” Emergency controls with role-based access
- **Audit Explorer** â€” Full-text search with facet filtering on all governance events
- **Approval Queue** â€” Human-in-the-loop oversight interface

## Regulatory Alignment
- **EU AI Act Article 12** â€” Automatic logging (âœ… hash-chained audit)
- **EU AI Act Article 14** â€” Human oversight with kill switch (âœ… built-in)
- **EU AI Act Article 11** â€” Technical documentation (âœ… policy-as-code)
- **SOC 2** â€” Audit trail and access controls (âœ… permission-gated immutability)
- **HIPAA** â€” Audit logging for PHI access (âœ… separate audit trail product)
- **NIST AI RMF** â€” Risk management framework mapping (âœ… trust scoring)

## Competitive Differentiation
- **Kernel-level enforcement** â€” Not a policy dashboard; governance embedded in runtime
- **Non-bypassable** â€” Like PostgreSQL RLS, enforced below application layer
- **Immutable audit** â€” Hash-chained, append-only, S3 Object Lock COMPLIANCE mode
- **Kill switch as first-class** â€” EU AI Act Article 14 compliant by design
- **Governance tokens** â€” Data gravity through non-portable `gt_` token accumulation

## Integration Patterns
- **LangChain** â€” Callback handler intercepts tool calls
- **CrewAI** â€” Task-level governance hooks
- **AutoGen** â€” Agent conversation interceptors
- **OpenAI Agents SDK** â€” Built-in `guardrails` parameter
- **Anthropic SDK** â€” Message-level policy evaluation
- **Kimi k1.6** â€” Tool use interception via middleware

## Common Recipes
1. Refund approval over $1,000 â†’ require_approval
2. Email sending rate limit â†’ rate_limit 100/hour
3. Database write protection â†’ deny on production without approval
4. Multi-agent coordination â†’ require_auth between agents
5. High-risk action approval â†’ require_approval + comprehensive audit
6. Agent-to-agent authentication â†’ gt_ token exchange
7. Audit export for regulator â†’ generate compliance proof package
8. Emergency shutdown â†’ kill switch all agents in namespace
9. Multi-tenant deployment â†’ RLS tenant isolation per customer
10. Compliance proof generation â†’ hash chain verification report

## Error Codes
- `citadel_001` â€” Policy denied action
- `citadel_002` â€” Approval required
- `citadel_003` â€” Rate limit exceeded (429)
- `citadel_004` â€” Agent not authenticated (401)
- `citadel_005` â€” Kill switch activated
- `citadel_006` â€” Audit trail unavailable
- `citadel_007` â€” Trust score below threshold
- `citadel_008` â€” Invalid governance token
- `citadel_009` â€” Subscription Payment Required (402)
- `citadel_010` â€” Usage Quota Exceeded (429)

## Rate Limits
- Free tier: 1,000 governed actions/day
- Pro tier: 100,000 governed actions/day
- Enterprise: Unlimited + dedicated infrastructure
- Burst limit: 10x base rate for 60 seconds

## Webhook Events
- `governance.action.allowed` â€” Action passed policy check
- `governance.action.denied` â€” Action blocked
- `governance.approval.required` â€” Human approval queued
- `governance.kill_switch.activated` â€” Emergency halt triggered
- `governance.trust_score.changed` â€” Agent trust score updated
- `governance.audit.exported` â€” Compliance package generated

## Production Deployment
- Docker image: `CITADEL/sdk:latest`
- Helm chart for Kubernetes
- Sidecar pattern for existing agent deployments
- Terraform modules for AWS/Azure/GCP
- Health check endpoint: `/healthz`
- Metrics endpoint: `/metrics` (Prometheus format)

## Security Best Practices
1. Rotate API keys every 90 days
2. Use separate API keys per environment (dev/staging/prod)
3. Enable IP allowlisting for production
4. Configure audit event forwarding to SIEM
5. Enable MFA for dashboard access
6. Regular compliance proof verification
7. Kill switch testing in staging monthly

## Performance
- Policy evaluation latency: <5ms p99
- Audit log ingestion: 10,000 events/second
- Kill switch propagation: <100ms across all agents
- Dashboard query response: <200ms for 30-day window

## Support
- Documentation: https://docs.CITADEL.dev
- API Status: https://status.CITADEL.dev
- Community Discord: https://discord.gg/CITADEL
- Enterprise Support: support@CITADEL.dev
