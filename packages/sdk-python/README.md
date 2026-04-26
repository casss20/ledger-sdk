# Citadel Governance SDK for Python

AI governance for agent builders — one primitive to control, audit, and approve every action your agents take.

## Installation

```bash
pip install citadel-governance
```

## Quickstart (recommended import)

```python
import citadel_governance as cg

cg.configure(
    base_url="https://api.citadelsdk.com",
    api_key="your-api-key",
    actor_id="my-agent",
)

result = await cg.execute(
    action="email.send",
    resource="user:123",
    payload={"to": "user@example.com", "subject": "Hello"},
)

if result.status == "executed":
    print("Sent!")
elif result.status == "pending_approval":
    print("Waiting for human review")
else:
    print(f"Blocked: {result.reason}")
```

## Legacy import (deprecated)

```python
import citadel  # deprecated — will be removed in v1.0
```

The `citadel` import path is kept for backward compatibility but emits a
`DeprecationWarning`. Please migrate to `citadel_governance`.

## Decorator

```python
import citadel_governance as cg

cg.configure(...)

@cg.guard(action="stripe.refund", resource="charge:{charge_id}")
async def refund(charge_id: str, amount: int):
    return stripe.refund.create(charge=charge_id, amount=amount)
```

## Context manager

```python
async with cg.CitadelClient(base_url="https://api.citadelsdk.com") as client:
    result = await client.execute(action="db.write", resource="users")
```

## Dashboard

Monitor all agent activity, approve requests, and manage policies at:
**https://dashboard.citadelsdk.com**

## Links

- **Documentation:** https://citadelsdk.com/docs
- **Dashboard:** https://dashboard.citadelsdk.com
- **PyPI:** https://pypi.org/project/citadel-governance/
- **Source:** https://github.com/casss20/citadel-sdk

## Testing & Certification

This package is validated before every release. See the [QA Gate Evidence](docs/QA_GATE_EVIDENCE.md) document for:

- Build artifact verification (wheel + sdist)
- Packaging compliance (`twine check`)
- Fresh-environment installation tests
- Import-path and backward-compatibility checks
- Smoke tests (happy path + failure path)
- Integration tests against realistic HTTP endpoints
- PyPI live-install verification
- Full unit test suite results

## License

Apache License 2.0

This SDK is open-source. The Citadel runtime uses a different (BSL-style) license. See the root `LICENSE` file for details.
