"""
Example: Wire governance around agent actions.

Shows how to use the @governed decorator to gate risky operations.
Run: python examples/governed_actions.py
"""

import asyncio
import os
import sys

# Add src to path for example
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ledger.sdk import Ledger, Denied


async def main():
    print("🔷 Ledger SDK Governance Examples")
    print("=" * 60)

    # Initialize governance
    dsn = os.getenv("AUDIT_DSN", "postgresql://postgres:password@localhost/postgres")
    gov = Ledger(audit_dsn=dsn, agent="demo")
    await gov.start()

    # Mock approval hook that auto-approves for demo
    async def approve_all(ctx: dict) -> bool:
        print(f"  [Approval] {ctx.get('action')} on {ctx.get('resource')} — auto-approved")
        return True

    gov.set_approval_hook(approve_all)

    # Example 1: Govern a campaign creation action
    @gov.governed(action="publish", resource="campaign", flag="campaign_publish")
    async def create_ad_campaign(name: str, budget: float) -> dict:
        """Create an ad campaign."""
        return {"status": "created", "campaign_name": name, "budget": budget}

    # Register kill switch
    gov.killsw.register("campaign_publish", enabled=True)

    # Test 1: Normal creation
    print("\n=== Test 1: Normal campaign creation ===")
    try:
        result = await create_ad_campaign("Black Friday Sale", 500.0)
        print(f"  ✅ Campaign created: {result}")
    except Denied as e:
        print(f"  ❌ Denied: {e}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 2: Kill the flag
    print("\n=== Test 2: Kill switch activated ===")
    gov.killsw.kill("campaign_publish", reason="budget exceeded policy")
    try:
        result = await create_ad_campaign("Cyber Monday Sale", 200.0)
        print(f"  ✅ Campaign created: {result}")
    except Denied as e:
        print(f"  ❌ Blocked by kill switch: {e}")

    # Test 3: Revive and retry
    print("\n=== Test 3: Kill switch revived ===")
    gov.killsw.revive("campaign_publish")
    try:
        result = await create_ad_campaign("New Year Sale", 300.0)
        print(f"  ✅ Campaign created: {result}")
    except Denied as e:
        print(f"  ❌ Denied: {e}")

    # Test 4: Govern an email send
    @gov.governed(action="send_message", resource="email")
    async def send_notification_email(to: str, subject: str) -> dict:
        return {"sent": True, "to": to, "subject": subject}

    print("\n=== Test 4: Email governance ===")
    try:
        result = await send_notification_email("user@example.com", "Welcome!")
        print(f"  ✅ Email sent: {result}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 5: Check audit integrity
    print("\n=== Test 5: Audit integrity ===")
    try:
        ok, entries = await gov.audit.verify_integrity()
        print(f"  Audit chain integrity: {ok} ({entries} entries)")
    except Exception as e:
        print(f"  Audit check skipped (no Postgres): {e}")

    await gov.stop()
    print("\n✅ Demo complete")


if __name__ == "__main__":
    asyncio.run(main())
