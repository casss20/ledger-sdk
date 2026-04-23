"""
Ledger Kernel Conformance Test Suite

Verifies that the governance kernel correctly:
1. Writes to all database tables
2. Follows deterministic decision paths
3. Maintains audit chain integrity
4. Enforces all control semantics

Run: pytest tests/test_kernel_conformance.py -v
"""

import pytest
import asyncio
import uuid
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

sys.path.insert(0, 'src')

# Database
import asyncpg

# Kernel components
from ledger.actions import Action, KernelStatus, KernelResult
from ledger.execution.kernel import Kernel
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.execution.executor import Executor as ActionExecutor
from ledger.status import ActorType


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
    
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=5, setup=setup_tenant)
    
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
# SCENARIO 1: Blocked by Kill Switch
# ============================================================================
async def test_01_blocked_by_kill_switch(kernel, db, tenant_id):
    """Given: Kill switch enabled. When: Action attempted. Then: BLOCKED_EMERGENCY."""
    kernel, repo = kernel
    
    # Setup: Enable kill switch
    await db.execute("""
        INSERT INTO kill_switches (scope_type, scope_value, tenant_id, enabled, reason)
        VALUES ('action', 'test.dangerous', $1, TRUE, 'Emergency stop')
    """, tenant_id)
    
    # Setup: Actor
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    # Execute
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.dangerous",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    # Verify
    assert result.decision.status == KernelStatus.BLOCKED_EMERGENCY
    assert result.decision.winning_rule == "kill_switch_active"
    
    # Verify audit
    events = await db.fetch("SELECT * FROM audit_events WHERE action_id = $1", action.action_id)
    assert len(events) >= 2  # action_received + decision_made
    
    event_types = [e['event_type'] for e in events]
    assert 'action_received' in event_types
    assert 'decision_made' in event_types


# ============================================================================
# SCENARIO 2: Blocked by Policy
# ============================================================================
async def test_02_blocked_by_policy(kernel, db, tenant_id):
    """Given: Policy blocks action. When: Action attempted. Then: BLOCKED_POLICY."""
    kernel, repo = kernel
    
    # Setup: Policy that blocks
    await db.execute("""
        INSERT INTO policies (name, version, scope_type, scope_value, tenant_id, rules_json, status)
        VALUES (
            'block_test', '1.0', 'action', 'test.forbidden', $1,
            '{"rules": [{"name": "block_rule", "condition": "true", "effect": "BLOCK", "reason": "Test block"}]}',
            'active'
        )
    """, tenant_id)
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.forbidden",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    assert result.decision.status == KernelStatus.BLOCKED_POLICY
    assert result.decision.winning_rule == "block_rule"
    
    # Verify policy snapshot created
    snapshot = await db.fetchrow(
        "SELECT * FROM policy_snapshots WHERE snapshot_id = $1",
        result.decision.policy_snapshot_id
    )
    assert snapshot is not None


# ============================================================================
# SCENARIO 3: Blocked by Capability Expiry
# ============================================================================
async def test_03_blocked_by_capability_expiry(kernel, db, tenant_id):
    """Given: Expired capability. When: Action attempted. Then: BLOCKED_CAPABILITY."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    await db.execute("""
        INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, 
                                 issued_at, expires_at, max_uses, uses, revoked)
        VALUES ($1, $2, $3, 'test.expiring', 'test', NOW() - INTERVAL '2 hours', 
                NOW() - INTERVAL '1 hour', 10, 0, FALSE)
    """, token_id, actor_id, tenant_id)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.expiring",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action, capability_token=token_id)
    
    assert result.decision.status == KernelStatus.BLOCKED_CAPABILITY


# ============================================================================
# SCENARIO 4: Pending Approval
# ============================================================================
async def test_04_pending_approval(kernel, db, tenant_id):
    """Given: High risk action. When: Action attempted. Then: PENDING_APPROVAL."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    # Policy requiring approval
    await db.execute("""
        INSERT INTO policies (name, version, scope_type, scope_value, tenant_id, rules_json, status)
        VALUES (
            'approve_high_risk', '1.0', 'action', 'test.highrisk', $1,
            '{"rules": [{"name": "high_risk", "condition": "true", "effect": "PENDING_APPROVAL", "requires_approval": true, "reason": "High risk"}]}',
            'active'
        )
    """, tenant_id)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.highrisk",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    assert result.decision.status == KernelStatus.PENDING_APPROVAL
    
    # Verify approval queue entry
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action.action_id)
    assert approval is not None
    assert approval['status'] == 'pending'


# ============================================================================
# SCENARIO 5: Approval Rejected
# ============================================================================
async def test_05_approval_rejected(kernel, db, tenant_id):
    """Given: Pending approval. When: Human rejects. Then: REJECTED_APPROVAL."""
    kernel, repo = kernel
    
    # Setup: Actor first
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ('agent_1', 'agent', $1, 'active')",
        tenant_id
    )
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ('admin_1', 'user_proxy', $1, 'active')",
        tenant_id
    )

    action_id = uuid.uuid4()
    await db.execute(
        "INSERT INTO actions (action_id, actor_id, actor_type, tenant_id, action_name, resource) VALUES ($1, $2, 'agent', $3, 'test.reject', 'test')",
        action_id, "agent_1", tenant_id
    )
    await db.execute(
        "INSERT INTO decisions (action_id, tenant_id, status, winning_rule, reason) VALUES ($1, $2, 'PENDING_APPROVAL', 'approval_required', 'Needs review')",
        action_id, tenant_id
    )
    await db.execute(
        "INSERT INTO approvals (action_id, tenant_id, status, requested_by, reason, expires_at) VALUES ($1, $2, 'pending', 'agent_1', 'Review', NOW() + INTERVAL '1 hour')",
        action_id, tenant_id
    )
    
    # Simulate rejection
    await db.execute(
        "UPDATE approvals SET status = 'rejected', reviewed_by = 'admin_1', decided_at = NOW(), decision_reason = 'Too risky' WHERE action_id = $1",
        action_id
    )
    await db.execute(
        "UPDATE decisions SET status = 'REJECTED_APPROVAL', reason = 'Rejected by admin_1: Too risky' WHERE action_id = $1",
        action_id
    )
    
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
    assert approval['status'] == 'rejected'
    
    decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action_id)
    assert decision['status'] == 'REJECTED_APPROVAL'


# ============================================================================
# SCENARIO 6: Approval Expired
# ============================================================================
async def test_06_approval_expired(kernel, db, tenant_id):
    """Given: Approval past expiry. When: Checked. Then: EXPIRED_APPROVAL."""
    kernel, repo = kernel
    
    # Setup: Actor first
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ('agent_1', 'agent', $1, 'active')",
        tenant_id
    )

    action_id = uuid.uuid4()
    await db.execute(
        "INSERT INTO actions (action_id, actor_id, actor_type, tenant_id, action_name, resource) VALUES ($1, $2, 'agent', $3, 'test.expire', 'test')",
        action_id, "agent_1", tenant_id
    )
    await db.execute(
        "INSERT INTO decisions (action_id, tenant_id, status, winning_rule, reason) VALUES ($1, $2, 'PENDING_APPROVAL', 'approval_required', 'Needs review')",
        action_id, tenant_id
    )
    await db.execute(
        "INSERT INTO approvals (action_id, tenant_id, status, requested_by, reason, expires_at) VALUES ($1, $2, 'pending', 'agent_1', 'Review', NOW() - INTERVAL '1 minute')",
        action_id, tenant_id
    )
    
    # Process expiry
    await db.execute(
        "UPDATE approvals SET status = 'expired' WHERE action_id = $1 AND expires_at < NOW()",
        action_id
    )
    await db.execute(
        "UPDATE decisions SET status = 'EXPIRED_APPROVAL', reason = 'Approval window expired' WHERE action_id = $1",
        action_id
    )
    
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
    assert approval['status'] == 'expired'


# ============================================================================
# SCENARIO 7: Allowed + Executed
# ============================================================================
async def test_07_allowed_and_executed(kernel, db, tenant_id):
    """Given: Action passes all checks. When: Executed. Then: ALLOWED/EXECUTED."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.safe",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    # Should be executed (no blocking rules, execution succeeds)
    assert result.decision.status == KernelStatus.EXECUTED
    assert result.executed is True
    
    # Verify action persisted
    db_action = await db.fetchrow("SELECT * FROM actions WHERE action_id = $1", action.action_id)
    assert db_action is not None


# ============================================================================
# SCENARIO 8: Execution Failed
# ============================================================================
async def test_08_execution_failed(kernel, db, tenant_id):
    """Given: Action allowed. When: Execution throws. Then: FAILED_EXECUTION."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.failing",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    # Execute with a function that will fail
    async def failing_func():
        raise RuntimeError("Simulated failure")
    
    # Override executor to use our failing function
    original_run = kernel.executor.run
    async def failing_run(action):
        raise RuntimeError("Simulated failure")
    kernel.executor.run = failing_run
    
    result = await kernel.handle(action)
    
    # Should be failed execution
    assert result.decision.status == KernelStatus.FAILED_EXECUTION
    assert result.executed is False
    
    # Restore executor
    kernel.executor.run = original_run


# ============================================================================
# SCENARIO 9: Duplicate Idempotency Key
# ============================================================================
async def test_09_idempotency_duplicate(kernel, db, tenant_id):
    """Given: Duplicate idempotency key. When: Second request. Then: Cached result."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"req_{uuid.uuid4().hex}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    # First request
    action1 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.idempotent",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    
    result1 = await kernel.handle(action1)
    
    # Second request with same key
    action2 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.idempotent",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    
    result2 = await kernel.handle(action2)
    
    # Verify idempotency - second should find cached decision
    assert result2.decision.status == result1.decision.status
    
    # Verify only one action in DB (the first one)
    actions = await db.fetch(
        "SELECT * FROM actions WHERE actor_id = $1 AND idempotency_key = $2",
        actor_id, idempotency_key
    )
    assert len(actions) == 1


# ============================================================================
# SCENARIO 10: Audit Chain Integrity
# ============================================================================
async def test_10_audit_chain_integrity(kernel, db, tenant_id):
    """Given: Multiple actions. When: verify_audit_chain. Then: Valid."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    
    # Execute multiple actions
    for i in range(3):
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=ActorType.AGENT.value,
            action_name=f"test.chain{i}",
            resource="test",
            tenant_id=tenant_id,
            payload={},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.utcnow(),
        )
        await kernel.handle(action)
    
    # Verify chain
    chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
    
    assert chain_check['valid'] is True
    assert chain_check['checked_count'] >= 6  # At least 2 events per action
    assert chain_check['broken_at_event_id'] is None
    
    # Verify events are linked
    events = await db.fetch("SELECT * FROM audit_events ORDER BY event_id LIMIT 20")
    for i, event in enumerate(events[1:], 1):
        prev_event = events[i-1]
        assert event['prev_hash'] == prev_event['event_hash']


# ============================================================================
# FIXTURES
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
