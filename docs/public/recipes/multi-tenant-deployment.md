# Recipe: Multi-Tenant Deployment

## What you'll learn

- Isolate tenants with RLS policies
- Share infrastructure safely
- Audit per-tenant
- Configure tenant-specific policies

---

## Use Case
You run a SaaS platform where each customer has their own agents. Data and governance must be isolated per tenant.

---

## Tenant Setup

```python
# Create tenant
tenant = CITADEL.tenants.create(
    name="acme-corp",
    plan="enterprise"
)

# Set tenant context for all operations
CITADEL.context.set_tenant(tenant.id)
```

---

## RLS Isolation

Policies automatically enforce tenant isolation:

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: tenant-isolation
  namespace: saas-platform
spec:
  trigger:
    any:
      - action: "*"
  enforcement:
    type: rls_filter
    tenant_field: tenant_id
```

---

## Per-Tenant Audit

```python
# Query only acme-corp's audit trail
records = CITADEL.audit.query(
    tenant_id="acme-corp",
    start="2026-04-01"
)

# Generate tenant-specific compliance report
report = CITADEL.compliance.export(
    tenant_id="acme-corp",
    framework="soc2",
    period="2026-Q1"
)
```

---

## Next steps

- [Core Concepts: Policies](../core-concepts/policies.md)
- [Guide: Production Deployment](../guides/production-deployment.md)
