# Citadel SDK for Python

AI governance for agent builders — one primitive to control, audit, and approve every action your agents take.

## Installation

```bash
pip install "citadel-sdk @ git+https://github.com/casss20/ledger-sdk.git#subdirectory=packages/sdk-python"
```

## Quickstart

```python
import citadel

citadel.configure(
    base_url="https://ledger-sdk.fly.dev",
    api_key="your-api-key",
    actor_id="my-agent",
)

result = await citadel.execute(
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

## Decorator

```python
@citadel.guard(action="stripe.refund", resource="charge:{charge_id}")
async def refund(charge_id: str, amount: int):
    return stripe.refund.create(charge=charge_id, amount=amount)
```

## Context manager

```python
async with citadel.CitadelClient(base_url="https://ledger-sdk.fly.dev") as client:
    result = await client.execute(action="db.write", resource="users")
```

## Dashboard

Monitor all agent activity, approve requests, and manage policies at:
**https://casss20-ledger-sdk-6nlu.vercel.app**

## License

MIT
