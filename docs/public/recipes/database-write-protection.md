# Recipe: Database Write Protection

## What you'll learn

- Block production database writes without approval
- Allow reads freely
- Require DBA approval for schema changes
- Audit all database access

---

## Use Case
Your data analysis agent needs to read production data but should never write to it. Schema changes need DBA approval.

---

## Policies

### Block production writes
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: block-production-writes
spec:
  trigger:
    action: database.write
    condition: environment == "production"
  enforcement:
    type: deny
```

### Allow production reads
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: allow-production-reads
spec:
  trigger:
    action: database.read
    condition: environment == "production"
  enforcement:
    type: allow
```

### Schema changes need DBA
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: schema-change-approval
spec:
  trigger:
    action: database.schema_change
  enforcement:
    type: require_approval
    approvers: [role:dba]
```

---

## SDK Implementation

```python
# Read (allowed)
read_action = citadel.govern(
    agent_id="analytics-agent",
    action="database.read",
    params={"table": "users", "environment": "production"}
)
result = read_action.execute()  # Success

# Write (denied)
write_action = citadel.govern(
    agent_id="analytics-agent",
    action="database.write",
    params={"table": "users", "environment": "production"}
)
try:
    write_action.execute()
except CITADEL_sdk.PolicyDeniedError:
    print("Write blocked - production is read-only")
```

---

## Next steps

- [Core Concepts: Policies](../core-concepts/policies.md)
- [Recipe: Multi-Tenant Deployment](multi-tenant-deployment.md)
