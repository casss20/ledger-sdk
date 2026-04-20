#!/usr/bin/env python3
"""
Ledger Canonical Demo: db.delete

Shows the complete governance lifecycle:
1. Action submitted
2. Decision made (allowed or blocked)
3. Approval or block
4. Audit verified

Run: python3 demos/demo_db_delete.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta

import asyncpg

from ledger.kernel import Kernel, Action, KernelStatus
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.executor import Executor as ActionExecutor
from ledger.status import ActorType


DEMO_DSN = "postgresql://ledger:ledger@127.0.0.1:5432/ledger"


async def setup_demo_data(pool: asyncpg.Pool):
    """Set up actors, policies, and capabilities for the demo."""
    async with pool.acquire() as conn:
        # Clean slate
        await conn.execute("""
            TRUNCATE actors, policies, policy_snapshots, capabilities, 
                        kill_switches, approvals, actions, decisions, 
                        audit_events, execution_results 
            CASCADE
        """)
        
        # Create actors
        await conn.execute("""
            INSERT INTO actors (actor_id, actor_type, status) VALUES 
            ('demo_admin', 'user_proxy', 'active'),
            ('demo_service', 'service', 'active')
        """)
        
        # Create policy: db.delete requires approval in production
        policy_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO policies (policy_id, name, version, scope_type, scope_value, rules_json, status)
            VALUES ($1, 'delete_protection', '1.0', 'action', 'db.delete', $2, 'active')
            """,
            policy_id,
            '{"rules": [{"name": "production_delete", "effect": "PENDING_APPROVAL", "condition": {"action_name": "db.delete", "environment": "production"}}]}'
        )
        
        # Create capability for fast-path deletes
        await conn.execute(
            """
            INSERT INTO capabilities (token_id, actor_id, action_scope, resource_scope, expires_at, max_uses)
            VALUES ('cap_fast_delete', 'demo_service', 'db.*', 'db', NOW() + interval '1 hour', 10)
            """
        )
        
        print("✅ Demo data ready")


async def demo_allowed_fast_path(kernel: Kernel):
    """Demo: Service with capability — fast path, no approval."""
    print("\n🚀 DEMO 1: Fast Path (capability present)")
    print("-" * 50)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="demo_service",
        actor_type=ActorType.SERVICE.value,
        action_name="db.delete",
        resource="db.users",
        tenant_id="demo",
        payload={"table": "users", "where": "id = 123"},
        context={"environment": "production"},
        session_id="demo_session_1",
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action, capability_token="cap_fast_delete")
    
    print(f"Action:     db.delete on db.users")
    print(f"Actor:      demo_service (with capability)")
    print(f"Decision:   {result.decision.status.value}")
    print(f"Winning:    {result.decision.winning_rule}")
    print(f"Executed:   {result.executed}")
    print(f"Result:     {result.result}")


async def demo_pending_approval(kernel: Kernel):
    """Demo: No capability — requires human approval."""
    print("\n⏳ DEMO 2: Pending Approval (no capability)")
    print("-" * 50)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="demo_admin",
        actor_type=ActorType.USER_PROXY.value,
        action_name="db.delete",
        resource="db.orders",
        tenant_id="demo",
        payload={"table": "orders", "where": "created_at < '2024-01-01'"},
        context={"environment": "production"},
        session_id="demo_session_2",
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    print(f"Action:     db.delete on db.orders")
    print(f"Actor:      demo_admin (no capability)")
    print(f"Decision:   {result.decision.status.value}")
    print(f"Winning:    {result.decision.winning_rule}")
    print(f"Reason:     {result.decision.reason}")
    print(f"Executed:   {result.executed}")
    
    # Show pending approval in queue
    async with kernel.repo.pool.acquire() as conn:
        approval = await conn.fetchrow(
            "SELECT * FROM approvals WHERE action_id = $1",
            action.action_id
        )
        if approval:
            print(f"Approval:   {approval['approval_id']} (status: {approval['status']})")


async def demo_kill_switch(kernel: Kernel):
    """Demo: Kill switch blocks everything."""
    print("\n🛑 DEMO 3: Kill Switch (emergency stop)")
    print("-" * 50)
    
    # Activate kill switch
    async with kernel.repo.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO kill_switches (scope_type, scope_value, enabled, reason)
            VALUES ('action', 'db.delete', true, 'security_incident')
            """
        )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="demo_service",
        actor_type=ActorType.SERVICE.value,
        action_name="db.delete",
        resource="db.users",
        tenant_id="demo",
        payload={"table": "users", "where": "id = 999"},
        context={"environment": "production"},
        session_id="demo_session_3",
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action, capability_token="cap_fast_delete")
    
    print(f"Action:     db.delete on db.users")
    print(f"Actor:      demo_service (WITH capability)")
    print(f"Decision:   {result.decision.status.value}")
    print(f"Winning:    {result.decision.winning_rule}")
    print(f"Reason:     {result.decision.reason}")
    print(f"Executed:   {result.executed}")
    
    # Deactivate kill switch
    async with kernel.repo.pool.acquire() as conn:
        await conn.execute(
            "UPDATE kill_switches SET enabled = false WHERE scope_value = 'db.delete'"
        )


async def demo_audit_verification(kernel: Kernel):
    """Demo: Verify the audit chain."""
    print("\n🔍 DEMO 4: Audit Verification")
    print("-" * 50)
    
    async with kernel.repo.pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM verify_audit_chain()")
    
    print(f"Chain valid:     {result['valid']}")
    print(f"Events checked:  {result['checked_count']}")
    
    if result['broken_at_event_id']:
        print(f"⚠️  Broken at:     {result['broken_at_event_id']}")
    else:
        print("✅ Chain integrity confirmed")
    
    # Show recent events
    async with kernel.repo.pool.acquire() as conn:
        events = await conn.fetch(
            "SELECT event_id, event_type, event_hash, prev_hash FROM audit_events ORDER BY event_id DESC LIMIT 5"
        )
    
    print("\nRecent audit events:")
    for event in events:
        print(f"  {event['event_id']:3d} | {event['event_type']:20s} | {event['event_hash'][:16]}... | prev: {event['prev_hash'][:16]}...")


async def main():
    """Run all demos."""
    print("=" * 60)
    print("LEDGER GOVERNANCE KERNEL — Canonical Demo")
    print("Action: db.delete (production database deletion)")
    print("=" * 60)
    
    # Setup
    pool = await asyncpg.create_pool(DEMO_DSN, min_size=1, max_size=5)
    await setup_demo_data(pool)
    
    # Build kernel
    repo = Repository(pool)
    policy_resolver = PolicyResolver(repo)
    policy_evaluator = PolicyEvaluator()
    precedence = Precedence(repo, policy_evaluator)
    approval_service = ApprovalService(repo)
    capability_service = CapabilityService(repo)
    audit_service = AuditService(repo)
    executor = ActionExecutor()
    
    kernel = Kernel(
        repository=repo,
        policy_resolver=policy_resolver,
        precedence=precedence,
        approval_service=approval_service,
        capability_service=capability_service,
        audit_service=audit_service,
        executor=executor,
    )
    
    # Run demos
    await demo_allowed_fast_path(kernel)
    await demo_pending_approval(kernel)
    await demo_kill_switch(kernel)
    await demo_audit_verification(kernel)
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
