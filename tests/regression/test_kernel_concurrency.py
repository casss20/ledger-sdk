"""
CITADEL Kernel Concurrency & Adversarial Test Suite

Tests the kernel under:
- Racing capability consumption
- Concurrent duplicate idempotency submissions  
- Approval state changes mid-flight
- Parallel audit writes under load
- Kill switch toggled during execution

Run: pytest tests/test_kernel_concurrency.py -v
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import asyncpg

from citadel.actions import Action, KernelStatus, KernelResult
from citadel.execution.kernel import Kernel
from citadel.repository import Repository
from citadel.policy_resolver import PolicyResolver, PolicyEvaluator
from citadel.precedence import Precedence
from citadel.approval_service import ApprovalService
from citadel.capability_service import CapabilityService
from citadel.audit_service import AuditService
from citadel.execution.executor import Executor as ActionExecutor
from citadel.status import ActorType


@pytest.fixture
async def db(postgres_dsn, tenant_id):
    """Database connection with tenant context set."""
    conn = await asyncpg.connect(postgres_dsn)
    await conn.execute("SELECT set_tenant_context($1)", tenant_id)
    yield conn
    await conn.close()


@pytest.fixture
async def kernel(postgres_dsn, tenant_id):
    """Fresh kernel instance with tenant-scoped pool."""
    async def setup_tenant(conn):
        await conn.execute("SELECT set_tenant_context($1)", tenant_id)
    
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=10, setup=setup_tenant)
    
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
    
    yield kernel, repo
    
    await pool.close()


# ============================================================================
# SCENARIO 11: Racing Capability Consumption
# ============================================================================
async def test_11_racing_capability_consumption(kernel, db, tenant_id):
    """Given: 5 concurrent requests with same capability. When: All execute. Then: Only max_uses succeed."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex[:8]}"
    max_uses = 3
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    await db.execute(
        """
        INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, expires_at, max_uses)
        VALUES ($1, $2, $3, 'test.*', 'test', NOW() + interval '1 hour', $4)
        """,
        token_id, actor_id, tenant_id, max_uses
    )
    
    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=ActorType.AGENT.value,
            action_name="test.race",
            resource="test",
            tenant_id=tenant_id,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.utcnow(),
        )
        return await kernel.handle(action, capability_token=token_id)
    
    # Launch 5 concurrent requests
    results = await asyncio.gather(*[submit_action(i) for i in range(5)], return_exceptions=True)
    
    # Count successes vs failures
    successes = sum(1 for r in results if isinstance(r, KernelResult) and r.decision.status == KernelStatus.EXECUTED)
    failures = sum(1 for r in results if isinstance(r, KernelResult) and r.decision.status == KernelStatus.BLOCKED_CAPABILITY)
    exceptions = sum(1 for r in results if isinstance(r, Exception))
    
    assert successes == max_uses, f"Expected {max_uses} successes, got {successes}"
    assert failures == 5 - max_uses, f"Expected {5 - max_uses} failures, got {failures}"
    assert exceptions == 0, f"Unexpected exceptions: {exceptions}"
    
    # Verify capability use count in DB
    cap = await db.fetchrow("SELECT * FROM capabilities WHERE token_id = $1", token_id)
    assert cap['uses'] == max_uses


# ============================================================================
# SCENARIO 12: Concurrent Duplicate Idempotency
# ============================================================================
async def test_12_concurrent_idempotency_duplicate(kernel, db, tenant_id):
    """Given: 10 concurrent requests with same idempotency key. When: All execute. Then: Exactly 1 action inserted."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"concurrent_{uuid.uuid4().hex}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=ActorType.AGENT.value,
            action_name="test.idempotent_race",
            resource="test",
            tenant_id=tenant_id,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            created_at=datetime.utcnow(),
        )
        return await kernel.handle(action)
    
    # Launch 10 concurrent requests with same key
    results = await asyncio.gather(*[submit_action(i) for i in range(10)], return_exceptions=True)
    
    # All should return a valid result (no exceptions)
    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 10
    
    # All should have the same decision status (first one wins)
    statuses = {r.decision.status for r in valid_results}
    assert len(statuses) == 1
    
    # Verify exactly ONE action in DB
    actions = await db.fetch(
        "SELECT * FROM actions WHERE actor_id = $1 AND idempotency_key = $2",
        actor_id, idempotency_key
    )
    assert len(actions) == 1, f"Expected 1 action, got {len(actions)}"


# ============================================================================
# SCENARIO 13: Approval State Change Mid-Flight
# ============================================================================
async def test_13_approval_state_change_mid_flight(kernel, db, tenant_id):
    """Given: Action pending approval. When: Approved while another checks. Then: Consistent state."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    admin_id = f"admin_{uuid.uuid4().hex[:8]}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'user_proxy', $2, 'active')",
        admin_id, tenant_id
    )
    
    # Insert a policy requiring approval
    policy_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO policies (policy_id, tenant_id, name, version, scope_type, scope_value, rules_json, status)
        VALUES ($1, $2, 'approval_test', '1.0', 'action', 'test.approve', $3, 'active')
        """,
        policy_id, tenant_id,
        '{"rules": [{"name": "needs_approval", "effect": "PENDING_APPROVAL", "condition": {"always": true}}]}'
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.approve",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    # Submit action (creates pending approval)
    result1 = await kernel.handle(action)
    assert result1.decision.status == KernelStatus.PENDING_APPROVAL
    
    # Get the approval ID
    approval = await db.fetchrow(
        "SELECT * FROM approvals WHERE action_id = $1",
        action.action_id
    )
    assert approval is not None
    
    # Simulate concurrent approval and status check
    async def approve_action():
        await asyncio.sleep(0.01)  # Small delay
        await db.execute(
            """
            UPDATE approvals 
            SET status = 'approved', reviewed_by = $1, decided_at = NOW()
            WHERE approval_id = $2
            """,
            admin_id, approval['approval_id']
        )
    
    async def check_status():
        # Re-query the action's decision
        decision = await db.fetchrow(
            "SELECT * FROM decisions WHERE action_id = $1",
            action.action_id
        )
        return decision
    
    # Run approval and check concurrently
    await asyncio.gather(approve_action(), check_status())
    
    # Verify final state
    final_approval = await db.fetchrow(
        "SELECT * FROM approvals WHERE approval_id = $1",
        approval['approval_id']
    )
    assert final_approval['status'] == 'approved'
    assert final_approval['reviewed_by'] == admin_id
    assert final_approval['decided_at'] is not None


# ============================================================================
# SCENARIO 14: Parallel Audit Writes Under Load
# ============================================================================
async def test_14_parallel_audit_load(kernel, db, tenant_id):
    """Given: 50 concurrent actions. When: All execute. Then: Audit chain valid."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=ActorType.AGENT.value,
            action_name=f"test.load{idx % 5}",
            resource="test",
            tenant_id=tenant_id,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.utcnow(),
        )
        return await kernel.handle(action)
    
    # Launch 50 concurrent actions
    results = await asyncio.gather(*[submit_action(i) for i in range(50)], return_exceptions=True)
    
    # All should succeed
    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 50
    
    # Verify audit chain
    chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
    assert chain_check['valid'] is True
    assert chain_check['checked_count'] >= 50 * 2  # At least 2 events per action
    assert chain_check['broken_at_event_id'] is None


# ============================================================================
# SCENARIO 15: Kill Switch Toggled Mid-Flight
# ============================================================================
async def test_15_kill_switch_toggle_mid_flight(kernel, db, tenant_id):
    """Given: Kill switch toggled during execution. When: New actions submitted. Then: Blocked after toggle."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    # Insert an active kill switch
    switch_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO kill_switches (switch_id, tenant_id, scope_type, scope_value, enabled, reason)
        VALUES ($1, $2, 'action', 'test.toggle', true, 'emergency_stop')
        """,
        switch_id, tenant_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.toggle",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    # Should be blocked initially
    result1 = await kernel.handle(action)
    assert result1.decision.status == KernelStatus.BLOCKED_EMERGENCY
    
    # Disable kill switch
    await db.execute(
        "UPDATE kill_switches SET enabled = false WHERE switch_id = $1",
        switch_id
    )
    
    # Now should be allowed
    action2 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.toggle",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result2 = await kernel.handle(action2)
    assert result2.decision.status == KernelStatus.EXECUTED
    
    # Re-enable kill switch
    await db.execute(
        "UPDATE kill_switches SET enabled = true WHERE switch_id = $1",
        switch_id
    )
    
    # Should be blocked again
    action3 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.toggle",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result3 = await kernel.handle(action3)
    assert result3.decision.status == KernelStatus.BLOCKED_EMERGENCY


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
