"""
Example: Using Citadel SDK with Weft-inspired patterns

This file demonstrates all the patterns copied from Weft:
1. Native mocking
2. Compile-time validation
3. Dense syntax
4. Sidecar pattern
"""

import asyncio
from CITADEL.dense import gov
from CITADEL.mocking import mockable, MockRegistry, Mock
from CITADEL.validation import validate_at_startup, validate_config
from CITADEL.sidecar import PostgresSidecar, get_sidecar_registry
from governance import get_sdk

# Initialize governance
sdk = get_sdk()


# ============================================================================
# 1. DENSE SYNTAX - Compact, AI-friendly governance definitions
# ============================================================================

# Traditional verbose way:
# GOVERNANCE = {
#     "action": "send_email",
#     "resource": "outbound_email",
#     "risk": "HIGH",
#     "approval": "HARD",
#     "required_fields": ["to", "subject", "body"],
#     "max_daily": 100,
# }

# Dense way (fewer tokens, validated at definition):
EMAIL = gov.email(
    risk="HIGH",
    approval="HARD",
    limits="20/hour, 100/day"
)

STRIPE = gov.payment(
    name="stripe_charge",
    max_amount=10000.0,
    limits="10/hour, 50/day"
)

DB = gov.database(
    name="write_database",
    max_rows=10000,
    limits="100/hour, 1000/day"
)

# Custom action
GITHUB = gov.action(
    "github_action",
    resource="github",
    risk="HIGH",
    approval="HARD",
    requires="workflow, ref",
    optional="inputs, secrets",
    limits="10/hour, 50/day"
)

print("Dense rules defined:")
print(f"  EMAIL.action = {EMAIL.action}")
print(f"  STRIPE.max_amount = ${STRIPE.max_amount}")
print(f"  DB.required_fields = {EMAIL._parse_fields(EMAIL.requires)}")


# ============================================================================
# 2. COMPILE-TIME VALIDATION - Catch errors at startup
# ============================================================================

# This validates all governance rules at import time
if __name__ == "__main__":
    print("\n--- Compile-Time Validation ---")
    valid = validate_at_startup()
    print(f"Validation passed: {valid}")
    
    # Test validation of a single config
    bad_config = {
        "action": "Send-Email",  # Wrong: should be snake_case
        "resource": "email",
        "risk": "HIGH",
        "approval": "HARD",
    }
    
    issues = validate_config(bad_config)
    if issues:
        print(f"Found {len(issues)} issues in bad_config:")
        for issue in issues:
            print(f"  [{issue.severity.value}] {issue.field}: {issue.message}")
            if issue.suggestion:
                print(f"    ðŸ’¡ {issue.suggestion}")


# ============================================================================
# 3. NATIVE MOCKING - Replace any action with mock data
# ============================================================================

@mockable("send_email", return_type=dict)
@gov.governed(action="send_email")
async def send_email(to: str, subject: str, body: str):
    """Real implementation - sends actual email."""
    # ... SMTP code ...
    return {"message_id": "real_123", "status": "sent"}


async def demonstrate_mocking():
    print("\n--- Native Mocking ---")
    
    # Without mock - would hit real SMTP
    print("1. Without mock:")
    result = await send_email("test@example.com", "Hello", "Body")
    print(f"   Result: {result}")
    
    # Register mock
    MockRegistry.register(
        "send_email",
        lambda to, subject, body: {
            "message_id": "mock_12345",
            "status": "sent",
            "mocked": True,
            "timestamp": "2026-04-19T01:50:00Z"
        }
    )
    
    print("2. With mock registered:")
    result = await send_email("test@example.com", "Hello", "Body")
    print(f"   Result: {result}")
    
    # Clear mocks
    MockRegistry.clear()
    print("3. Mocks cleared, back to real implementation")
    
    # Context manager for temporary mocking
    print("4. Using context manager for temporary mock:")
    with Mock({"send_email": lambda **kwargs: {"status": "mocked_temp"}}):
        result = await send_email("test@example.com", "Hello", "Body")
        print(f"   Result: {result}")
    
    print("5. After context exit, mock is auto-cleared")


# ============================================================================
# 4. SIDECAR PATTERN - Infrastructure through isolated adapters
# ============================================================================

async def demonstrate_sidecar():
    print("\n--- Sidecar Pattern ---")
    
    # Create sidecar (in production, endpoint from env/K8s)
    pg_sidecar = PostgresSidecar("http://localhost:8081")
    
    try:
        # Initialize (gets connection info from sidecar)
        await pg_sidecar.initialize()
        
        # Core never talks to Postgres directly
        # Goes through sidecar for security isolation
        result = await pg_sidecar.query(
            "SELECT * FROM audit_log WHERE created_at > $1",
            {"since": "2026-04-01"}
        )
        print(f"Query result: {result}")
        
        # Check health
        healthy = await pg_sidecar.health()
        print(f"Sidecar healthy: {healthy}")
        
    except Exception as e:
        print(f"Sidecar error (expected if not running): {e}")
    finally:
        await pg_sidecar.close()


# ============================================================================
# 5. PUTTING IT ALL TOGETHER - A governed, validated, mockable action
# ============================================================================

@mockable("process_payment")
@gov.governed(action="process_payment", resource="stripe")
async def process_payment(
    amount: float,
    customer_id: str,
    db: PostgresSidecar = None
):
    """
    A fully governed, validated, mockable payment action.
    
    - Dense config defines the rules
    - Compile-time validation ensures config is correct
    - Mockable for testing without hitting Stripe
    - Sidecar for database access (isolated from core)
    """
    # 1. Validation happens at decoration time (compile-time)
    
    # 2. Mocking can replace this entire function in tests
    
    # 3. Risk classification (from dense config)
    if amount > STRIPE.max_amount:
        raise ValueError(f"Amount ${amount} exceeds max ${STRIPE.max_amount}")
    
    # 4. Database via sidecar (if provided)
    if db:
        await db.execute(
            "INSERT INTO payments (amount, customer_id) VALUES ($1, $2)",
            {"amount": amount, "customer_id": customer_id}
        )
    
    return {
        "charged": amount,
        "customer": customer_id,
        "status": "success"
    }


async def main():
    print("=" * 60)
    print("Citadel SDK - Weft-inspired Patterns Demo")
    print("=" * 60)
    
    # Show dense configs
    print("\n--- Dense Syntax Examples ---")
    for rule in [EMAIL, STRIPE, DB, GITHUB]:
        print(f"\n{rule.action}:")
        print(f"  risk={rule.risk}, approval={rule.approval}")
        print(f"  requires: {rule._parse_fields(rule.requires)}")
        print(f"  limits: {rule._parse_limits()}")
    
    # Demonstrate mocking
    await demonstrate_mocking()
    
    # Demonstrate sidecar
    await demonstrate_sidecar()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
