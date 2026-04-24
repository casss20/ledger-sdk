# Hash-Chained Audit Trail

## What you'll learn

- How the hash chain guarantees tamper evidence
- The dual-write architecture (immutable archive + searchable index)
- Querying and exporting audit records
- Compliance proof generation for regulators
- Independent verification without trusting Citadel

---

## Overview

Citadel's audit trail is an append-only, cryptographically signed log of every governance decision. It's designed to be:

- **Tamper-evident**: Any modification breaks the hash chain
- **Immutable**: Records cannot be deleted or altered
- **Verifiable**: Third parties can verify integrity without trusting Citadel
- **Correlatable**: W3C trace context links related actions across agents

---

## Hash Chain Structure

Each audit record contains:

```
Record N:
  - timestamp: 2026-04-23T10:30:00Z
  - action: email.send
  - decision: allowed
  - policy: email-allowed
  - agent_id: agent-01
  - gt_token: gt_1Aa2...
  - prev_hash: sha256(Record N-1)
  - content_hash: sha256(this record's content)
  - chain_hash: sha256(prev_hash + content_hash)
  - signature: ECDSA(chain_hash, Citadel private key)
```

The chain ensures that modifying any historical record invalidates all subsequent records.

---

## Dual-Write Architecture

Every audit record is written to two destinations simultaneously:

### 1. Immutable Archive (Compliance)
- **Storage**: S3 Object Lock COMPLIANCE mode
- **Property**: Even root account cannot delete
- **Retention**: Configurable (1-10+ years)
- **Access**: Read-only API, Admin role only
- **Format**: Compressed JSON Lines (JSONL)

### 2. Searchable Index (Operations)
- **Storage**: Elasticsearch/OpenSearch
- **Property**: Full-text search, facet filtering
- **Retention**: 90 days hot, 1-7 years warm
- **Access**: Dashboard, API, SIEM forwarding
- **Format**: Indexed JSON with mappings

```
Governed Action
    ↓
Record Created
    ↓
    ├─→ S3 Object Lock (Immutable Archive)
    └─→ Elasticsearch (Searchable Index)
```

---

## Querying the Audit Trail

### Basic query
```python
records = citadel.audit.query(
    agent_id="email-agent-01",
    start="2026-04-01",
    end="2026-04-30"
)
```

### Advanced filtering
```python
records = citadel.audit.query(
    decisions=["denied", "approval_required"],
    policies=["refund-approval-over-1000"],
    sort_by="timestamp",
    sort_order="desc",
    limit=100
)
```

### Full-text search
```python
records = citadel.audit.search(
    query="refund AND amount > 500",
    fields=["action", "params", "outcome"]
)
```

---

## Compliance Proof Generation

Generate a regulator-ready compliance package:

```python
package = citadel.audit.export_compliance_proof(
    start="2026-01-01",
    end="2026-03-31",
    format="pdf",  # or "json", "csv"
    include_verification=True  # Include hash chain verification
)

# Download the package
package.download("/path/to/compliance-q1-2026.pdf")
```

The package includes:
1. Complete audit record list
2. Hash chain verification report
3. Tamper-evidence attestation
4. Policy snapshot at time of action
5. Agent identity certificates

---

## Independent Verification

Verify the hash chain without trusting Citadel:

```python
# Fetch all records in a time range
records = citadel.audit.query(start="2026-04-01", end="2026-04-30")

# Verify chain integrity locally
previous_hash = None
for record in records:
    # Verify content hash
    computed_content = sha256(record.content)
    assert computed_content == record.content_hash

    # Verify chain link
    if previous_hash:
        computed_chain = sha256(previous_hash + record.content_hash)
        assert computed_chain == record.chain_hash

    previous_hash = record.chain_hash

print("All records verified. Chain is intact.")
```

> 💡 **Why this matters:** Regulators may ask you to prove your audit trail hasn't been tampered with. This verification proves it mathematically — not by trusting Citadel's word.

---

## W3C Trace Context Correlation

Distributed agents share trace context:

```python
# Agent A initiates action
action_a = citadel.govern(agent_id="agent-a", action="order.create")
result_a = action_a.execute()

# Pass trace context to Agent B
trace_context = result_a.trace_context

# Agent B continues the trace
action_b = citadel.govern(
    agent_id="agent-b",
    action="inventory.reserve",
    trace_context=trace_context  # Links to parent action
)
```

View correlated traces in dashboard:
```
Trace: trace-123e4567-e89b-12d3-a456-426614174000
├─ Agent A: order.create [allowed]
├─ Agent B: inventory.reserve [allowed]
├─ Agent C: payment.charge [require_approval]
└─ Human: approved payment.charge
```

---

## Retention and Lifecycle

| Phase | Duration | Storage | Query Speed | Cost |
|-------|----------|---------|-------------|------|
| Hot | 0-90 days | SSD index | <200ms | Included |
| Warm | 90 days-7 years | S3 Standard | 2-5 seconds | $0.01/GB |
| Cold | 7+ years | S3 Glacier | Minutes (rehydrate) | $0.001/GB |

Configure in settings:
```python
citadel.config.set_retention({
    "hot_days": 90,
    "warm_years": 7,
    "cold_indefinite": True
})
```

---

## Next steps

- [Governance Tokens](./governance-tokens.md) — Understand `gt_` tokens
- [Recipe: Audit Export for Regulator](../recipes/audit-export-for-regulator.md)
- [Recipe: Compliance Proof Generation](../recipes/compliance-proof-generation.md)
