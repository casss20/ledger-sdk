"""
End-to-end demo of LEDGER SDK.

Runs against local Postgres. Expects:
  postgres://postgres:password@localhost/postgres
"""

import asyncio
from ledger.sdk import Ledger, Denied


async def approve_everything(ctx):
    print(f"[approval] {ctx}")
    return True


async def main():
    gov = Ledger(
        audit_dsn="postgres://postgres:password@localhost/postgres",
        agent="nova",
    )
    await gov.start()
    
    gov.set_approval_hook(approve_everything)
    gov.killsw.register("email_send", enabled=True)

    @gov.governed(action="send_message", resource="email", flag="email_send")
    async def send_email(to, body):
        return {"to": to, "sent": True}

    # First call — approved
    print(await send_email("user@x.com", "hello"))

    # Kill the feature
    gov.killsw.kill("email_send", reason="phishing incident")

    # Second call — blocked
    try:
        await send_email("user@x.com", "again")
    except Denied as e:
        print(f"blocked: {e}")

    # Verify audit integrity
    ok, n = await gov.audit.verify_integrity()
    print(f"audit ok={ok} entries={n}")

    await gov.stop()


if __name__ == "__main__":
    asyncio.run(main())